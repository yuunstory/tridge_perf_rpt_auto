import os
import json
from typing import List, Dict, Any

def generate_ai_analysis(records: List[Dict[str, Any]], kpis: Dict[str, Any]) -> Dict[str, Any]:
    """
    취합 데이터 및 산출된 KPI를 기반으로 경영진 보고용 전문 비즈니스 텍스트를 생성합니다.
    GEMINI_API_KEY가 있는 경우 Gemini API를 사용하고, 없을 경우 고급 비즈니스 템플릿 엔진을 사용합니다.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if api_key:
        try:
            return call_gemini_api(records, kpis, api_key)
        except Exception as e:
            print(f"[Warning] Gemini API 호출 실패, 룰베이스 엔진으로 대체: {e}")

    # Fallback: 고급 비즈니스 룰베이스 문안 생성기
    return generate_rule_based_analysis(records, kpis)


def generate_rule_based_analysis(records: List[Dict[str, Any]], kpis: Dict[str, Any]) -> Dict[str, Any]:
    """
    데이터 수치와 부서별 성과를 심층 결합하여 대기업 기획조정실 스타일의 보고 문안을 생성합니다.
    """
    dept_cnt = kpis.get("department_count", 0)
    total_cnt = kpis.get("total_count", 0)
    fin_impact = kpis.get("total_financial_impact", 0.0)
    time_saved = kpis.get("total_time_saved", 0.0)
    db_count = kpis.get("total_db_count", 0)
    actions = kpis.get("total_actions", 0)
    avg_sat = kpis.get("avg_satisfaction", 0.0)

    # 최고 성과 부서 탐색
    top_record = max(records, key=lambda x: x.get("financial_impact", 0), default={})
    top_dept = top_record.get("department", "해당 없음")
    top_impact = top_record.get("financial_impact", 0)

    # 1. Executive Summary
    summary_p1 = (
        f"본 보고서는 전사 {dept_cnt}개 주요 사업 부서(상품소싱, 해외수출, 원료매입 등)의 "
        f"트릿지(Tridge Eye, Ark, Data Analytics) 데이터 솔루션 활용 실적을 종합 분석한 결과입니다. "
        f"금번 분기 총 {total_cnt}건의 전략 프로젝트가 가동되었으며, 글로벌 시장 인텔리전스 및 바이어 매칭 기능을 통해 "
        f"총 {fin_impact:,.0f}만 원 상당의 직접 재무 기여(원가 절감 및 수출 파이프라인 창출)와 "
        f"전사 총 {time_saved:,.0f}시간의 시장 리서치 공수 절감 효과를 달성하였습니다."
    )

    summary_p2 = (
        f"특히 {top_dept} 부서를 필두로 객관적 글로벌 단가 비교를 통한 구매 협상력 우위 확보, "
        f"동남아 및 북미 등 신규 권역 바이어 풀 {db_count}개사 발굴 및 {actions}건의 직접 비즈니스 액션(샘플/미팅)을 이끌어내며 "
        f"단순 정보 조회를 넘어 실질적인 사업화 및 원가 개선 성과로 연결되었습니다. "
        f"전사 평균 솔루션 만족도는 {avg_sat}점(5점 만점)으로 전반적인 데이터 신뢰도와 업무 기여도가 높게 평가되었습니다."
    )

    # 2. 3대 핵심 성과 (Top 3 Highlights)
    highlights = [
        {
            "title": f"직접 재무 기여 총 {fin_impact:,.0f}만 원 창출 (ROI 가시화)",
            "desc": f"원료 매입 단가 협상 타결 및 해외 수출 파이프라인 구축을 통해 솔루션 도입 비용 대비 뚜렷한 투자회수 성과 확보"
        },
        {
            "title": f"글로벌 타깃 DB {db_count}개사 확보 및 비즈니스 액션 {actions}건 전개",
            "desc": f"트릿지 아크 및 인텔리전스 기능을 통해 국내외 유효 바이어/공급사 발굴 리드타임을 대폭 단축하여 실질 거래 협의 단계 진입"
        },
        {
            "title": f"전사 리서치 소요 시간 {time_saved:,.0f}시간 단축 (업무 생산성 혁신)",
            "desc": f"기존 개별 에이전시 문의 및 분산 검색 방식 대비 약 60~75%의 조사 시간을 절감하여 신속한 의사결정 체계 확립"
        }
    ]

    # 3. 솔루션 평가 및 이슈 종합
    issues_summary = (
        "부서별 만족도는 5점 만점에 평균 " + str(avg_sat) + "점으로 양호하나, "
        "일부 품목(유기농, 세부 규격)에 대한 검색 필터링 고도화와 추천 바이어 리스트의 유효성 검증 강화가 공통 요구사항으로 집계되었습니다. "
        "트릿지 전담 CSM과의 정기 기술 미팅을 통해 해당 애로사항을 공식 안건으로 상정하고 데이터 정합성을 개선할 계획입니다."
    )

    # 4. 종합 제언 및 향후 로드맵
    strategic_recommendations = [
        f"【구독 유지 및 라이선스 재배분】: 고성과 부서({top_dept}, 해외수출 등)의 사용 권한을 확대하고, 비활성 부서는 교육 및 맞춤형 대시보드 지원으로 활용도 상향 평준화 추진",
        "【트릿지 CSM 협업 체계 고도화】: 단순 데이터 조회를 넘어 당사 맞춤형 글로벌 바이어 매칭 정밀도 제고를 위한 분기별 피드백 루프 정례화",
        "【원료/소싱 부서 모니터링 품목 다변화】: 기확보된 원가 절감 노하우를 바탕으로 곡물/과채류 등 모니터링 원자재 라인업을 5개 추가 확대하여 연간 1억 원 원가 절감 목표 수립"
    ]

    return {
        "executive_summary_paragraphs": [summary_p1, summary_p2],
        "highlights": highlights,
        "issues_summary": issues_summary,
        "strategic_recommendations": strategic_recommendations
    }


def call_gemini_api(records: List[Dict[str, Any]], kpis: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    Google Gemini REST API를 직접 호출하여 심층 보고 문안을 생성합니다.
    """
    import requests

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    prompt = f"""
당신은 대기업 최고전략책임자(CSO)이자 데이터 분석 전문가입니다.
아래 취합된 '트릿지(Tridge) B2B 농축수산/식품 데이터 솔루션' 활용 실적 데이터를 분석하여
경영진(C-Level) 보고용 성과보고서 본문 문안을 작성해 주세요.

[전사 KPI 집계 데이터]
{json.dumps(kpis, ensure_ascii=False, indent=2)}

[부서별 세부 활용 실적]
{json.dumps(records, ensure_ascii=False, indent=2)}

반드시 다음 JSON 포맷으로만 응답해 주세요 (마크다운 코드블록 없이 순수 JSON만 출력):
{{
  "executive_summary_paragraphs": [
    "경영진 요약 문단 1 (전체 도입 효과와 재무 기여, 리서치 시간 단축을 포함한 거시적 총평)",
    "경영진 요약 문단 2 (핵심 부서들의 성과와 비즈니스 전환 가치, 전사적 의미)"
  ],
  "highlights": [
    {{"title": "핵심 성과 1 제목", "desc": "세부 설명"}},
    {{"title": "핵심 성과 2 제목", "desc": "세부 설명"}},
    {{"title": "핵심 성과 3 제목", "desc": "세부 설명"}}
  ],
  "issues_summary": "솔루션 사용 시 발생한 부서별 이슈 및 트릿지(CSM) 대상 개선 요구사항 종합 분석 (1~2문장)",
  "strategic_recommendations": [
    "전략적 제언 1 (라이선스 재배분 및 구독 유지 타당성)",
    "전략적 제언 2 (트릿지 협업 및 데이터 품질 개선 방안)",
    "전략적 제언 3 (차기 분기 비즈니스 목표 및 확대 방안)"
  ]
}}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4}
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    return json.loads(text)
