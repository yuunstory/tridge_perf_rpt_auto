import re
import io
import json
import requests
import pandas as pd
from typing import List, Dict, Any, Tuple

# 표준 필드 매핑 딕셔너리
COLUMN_MAPPINGS = {
    "department": ["활용 파트", "활용 부서", "부서", "부서명", "파트"],
    "author": ["담당자", "작성자", "이름"],
    "solution": ["구분", "사용 솔루션", "솔루션", "솔루션 구분"],
    "period": ["활용 기간", "기간", "시작일", "진행 기간"],
    "goal": ["비즈니스 목표", "목표", "활용 목표"],
    "target": ["타깃 품목/국가", "타깃", "대상 품목", "품목/국가"],
    "status": ["진행 상태", "상태", "진행상태"],
    "activity": ["세부 활용 내용", "활용 내용", "내용", "주요 활동"],
    "valid_db_count": ["유효 DB 발굴 수 (개사)", "유효 DB 발굴 수", "유효 DB", "발굴 수", "바이어수"],
    "action_count": ["컨택/미팅/샘플 수 (건)", "컨택/미팅/샘플 수", "미팅 건수", "샘플 발송", "컨택수"],
    "financial_impact": ["재무 기여 추정액 (만원)", "재무 기여 추정액", "금액", "절감액", "기여 금액"],
    "time_saved_hours": ["리서치 절감 시간 (시간)", "리서치 절감 시간", "절감 시간", "시간 절감"],
    "qualitative_insight": ["핵심 성과 및 인사이트", "성과", "정성 성과", "인사이트"],
    "satisfaction": ["솔루션 만족도 (1~5)", "솔루션 만족도", "만족도"],
    "issue_and_request": ["이슈 및 트릿지 요청사항", "이슈 및 기타사항", "이슈", "요청사항"],
    "next_plan": ["차기 계획 및 목표", "다음 계획 및 목표", "차기 계획", "다음 계획"]
}

def extract_csv_url_from_google_sheet(sheet_url: str) -> str:
    """
    구글 스프레드시트 공유 링크 또는 웹 게시 링크에서 실시간 CSV 다운로드 URL을 추출합니다.
    """
    sheet_url = sheet_url.strip()

    if "output=csv" in sheet_url or "format=csv" in sheet_url:
        return sheet_url

    if "/pubhtml" in sheet_url:
        return sheet_url.replace("/pubhtml", "/pub?output=csv")
    if "/pub" in sheet_url:
        if "?" in sheet_url:
            return f"{sheet_url}&output=csv"
        return f"{sheet_url}?output=csv"

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if match:
        doc_id = match.group(1)
        gid_match = re.search(r"[#&?]gid=([0-9]+)", sheet_url)
        gid_param = f"&gid={gid_match.group(1)}" if gid_match else ""
        return f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv{gid_param}"

    raise ValueError("유효한 구글 스프레드시트 URL 형식이 아닙니다.")


def fetch_and_parse_google_sheets(sheet_url: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    구글 시트 URL을 통해 CSV를 다운로드받아 표준 레코드 리스트로 파싱합니다.
    """
    csv_url = extract_csv_url_from_google_sheet(sheet_url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(csv_url, headers=headers, timeout=12)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            "구글 스프레드시트를 가져오는 데 실패했습니다. 시트가 '링크가 있는 모든 사용자에게 보기 권한 허용' 상태인지 확인해 주세요."
        )

    content = response.content
    try:
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(io.BytesIO(content), encoding="cp949")

    df = df.dropna(how="all")

    parsed_records = []
    col_names = [str(c).strip() for c in df.columns]

    mapped_keys = {}
    for standard_key, aliases in COLUMN_MAPPINGS.items():
        for col in col_names:
            if col in aliases or any(alias in col for alias in aliases):
                mapped_keys[standard_key] = col
                break

    for idx, row in df.iterrows():
        dept_col = mapped_keys.get("department")
        dept_val = str(row[dept_col]).strip() if dept_col and pd.notna(row[dept_col]) else ""
        if not dept_val or dept_val.lower() == "nan" or "예시" in dept_val:
            continue

        def safe_num(key: str, default: float = 0.0) -> float:
            col = mapped_keys.get(key)
            if col and pd.notna(row[col]):
                val_str = str(row[col]).replace(",", "").replace("만원", "").replace("개", "").replace("건", "").replace("시간", "").strip()
                try:
                    return float(val_str)
                except ValueError:
                    return default
            return default

        def safe_str(key: str, default: str = "-") -> str:
            col = mapped_keys.get(key)
            if col and pd.notna(row[col]):
                val = str(row[col]).strip()
                return val if val.lower() != "nan" else default
            return default

        record = {
            "id": f"gsheet-{idx + 1}",
            "department": dept_val,
            "author": safe_str("author", "미입력"),
            "solution": safe_str("solution", "트릿지 아이"),
            "period": safe_str("period", "2026년 하반기"),
            "goal": safe_str("goal", "-"),
            "target": safe_str("target", "-"),
            "status": safe_str("status", "진행중"),
            "activity": safe_str("activity", "-"),
            "valid_db_count": int(safe_num("valid_db_count", 0)),
            "action_count": int(safe_num("action_count", 0)),
            "financial_impact": safe_num("financial_impact", 0.0),
            "time_saved_hours": safe_num("time_saved_hours", 0.0),
            "qualitative_insight": safe_str("qualitative_insight", "-"),
            "satisfaction": int(safe_num("satisfaction", 4)),
            "issue_and_request": safe_str("issue_and_request", "-"),
            "next_plan": safe_str("next_plan", "-"),
        }
        parsed_records.append(record)

    summary = {
        "total_rows_imported": len(parsed_records),
        "source_url": sheet_url
    }

    return parsed_records, summary


def append_record_to_google_sheet(web_app_url: str, record: Dict[str, Any]) -> bool:
    """
    웹 입력폼에서 등록된 실적을 Google Apps Script Web App을 통해 구글 스프레드시트에 즉시 새 행으로 추가합니다.
    """
    headers = {"Content-Type": "application/json"}
    
    # 구글 시트 순서에 맞춘 데이터 페이로드
    payload = {
        "department": record.get("department", ""),
        "author": record.get("author", ""),
        "solution": record.get("solution", ""),
        "period": record.get("period", ""),
        "goal": record.get("goal", ""),
        "target": record.get("target", ""),
        "status": record.get("status", ""),
        "activity": record.get("activity", ""),
        "valid_db_count": record.get("valid_db_count", 0),
        "action_count": record.get("action_count", 0),
        "financial_impact": record.get("financial_impact", 0),
        "time_saved_hours": record.get("time_saved_hours", 0),
        "qualitative_insight": record.get("qualitative_insight", ""),
        "satisfaction": record.get("satisfaction", 4),
        "issue_and_request": record.get("issue_and_request", ""),
        "next_plan": record.get("next_plan", "")
    }

    try:
        resp = requests.post(web_app_url, data=json.dumps(payload), headers=headers, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[Warning] 구글 스프레드시트 실시간 전송 실패: {e}")
        return False


def get_google_apps_script_code() -> str:
    """
    사용자가 구글 시트 메뉴 [확장 프로그램] -> [Apps Script]에 붙여넣기만 하면 
    웹 폼의 입력을 실시간으로 시트 맨 아래에 행으로 추가해주는 스크립트 코드
    """
    return """// [트릿지 성과보고서 자동 적재 Apps Script]
// 구글 스프레드시트 메뉴: 확장 프로그램 > Apps Script에 이 코드를 붙여넣고 [배포 > 새 배포 > 웹 앱] 실행
function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);
  
  sheet.appendRow([
    data.department || "",
    data.author || "",
    data.solution || "",
    data.period || "",
    data.goal || "",
    data.target || "",
    data.status || "",
    data.activity || "",
    data.valid_db_count || 0,
    data.action_count || 0,
    data.financial_impact || 0,
    data.time_saved_hours || 0,
    data.qualitative_insight || "",
    data.satisfaction || 4,
    data.issue_and_request || "",
    data.next_plan || ""
  ]);
  
  return ContentService.createTextOutput(JSON.stringify({status: "success"}))
    .setMimeType(ContentService.MimeType.JSON);
}
"""

def generate_google_sheets_template_excel(output_path: str):
    columns = [
        "활용 부서", "담당자", "사용 솔루션", "활용 기간", "비즈니스 목표", "타깃 품목/국가",
        "진행 상태", "세부 활용 내용", "유효 DB 발굴 수 (개사)", "컨택/미팅/샘플 수 (건)",
        "재무 기여 추정액 (만원)", "리서치 절감 시간 (시간)", "핵심 성과 및 인사이트",
        "솔루션 만족도 (1~5)", "이슈 및 트릿지 요청사항", "차기 계획 및 목표"
    ]

    example_rows = [
        [
            "상품소싱", "김소싱 매니저", "트릿지 아이", "2026/08/20 ~ 2026/10/20",
            "국내외 건강기능식품 소싱 트렌드 분석 및 신규 유망 품목 발굴", "유기농 비타민 원료 / 미국, 유럽",
            "완료", "국내외 매입 단가 현황 비교 및 소비 동향 파악", 28, 5, 1800, 24,
            "타깃 품목 2개 확정 및 후보 공급사 6개사 발굴 완료", 4,
            "유기농 인증 품목 검색 필터 세분화 필요", "선정된 상품군별 3개 공급사 대상 샘플 테스트"
        ],
        [
            "해외수출", "이수출 과장", "트릿지 아크", "2026/08/20 ~ 2026/10/26",
            "일본/동남아 타깃 상품 등록 및 해외 바이어 발굴", "프리미엄 스낵류 / 일본, 베트남",
            "진행중", "트릿지 아크 상품등록 및 글로벌 프로모션 캠페인 집행", 42, 8, 4500, 32,
            "일본 바이어 소포장 규격 니즈 확인 후 패키징 변경 피드백 전달", 3,
            "초기 추천 바이어 리스트 검증 강화 필요", "샘플 발송 바이어 2곳과 본계약 체결 협의"
        ]
    ]

    df = pd.DataFrame(example_rows, columns=columns)
    df.to_excel(output_path, index=False, engine="openpyxl")
