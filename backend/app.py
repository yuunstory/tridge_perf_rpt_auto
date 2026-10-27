import os
import io
import json
import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from backend.data_manager import load_records, save_records, calculate_kpis, SAMPLE_FILE, DATA_DIR, ensure_data_dir
from backend.google_sheets import (
    fetch_and_parse_google_sheets,
    generate_google_sheets_template_excel,
    append_record_to_google_sheet,
    get_google_apps_script_code
)
from backend.ai_analyzer import generate_ai_analysis
from backend.docx_generator import build_docx_report

app = FastAPI(title="Tridge Performance Report Automation System", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

def load_config() -> Dict[str, Any]:
    ensure_data_dir()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"sheet_url": "", "webhook_url": ""}

def save_config(cfg: Dict[str, Any]):
    ensure_data_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


class RecordModel(BaseModel):
    id: Optional[str] = None
    department: str
    author: str
    solution: str
    period: str
    goal: str
    target: str
    status: str
    activity: str
    valid_db_count: int
    action_count: int
    financial_impact: float
    time_saved_hours: float
    qualitative_insight: str
    satisfaction: int
    issue_and_request: str
    next_plan: str

class GoogleSheetSyncRequest(BaseModel):
    url: str
    mode: str = "overwrite"  # overwrite or append

class GoogleSheetConfigRequest(BaseModel):
    sheet_url: Optional[str] = ""
    webhook_url: Optional[str] = ""


@app.get("/api/records")
def get_all_records():
    records = load_records()
    kpis = calculate_kpis(records)
    cfg = load_config()
    return {
        "records": records,
        "kpis": kpis,
        "config": cfg
    }

@app.post("/api/records")
def create_record(record: RecordModel):
    records = load_records()
    rec_dict = record.dict()
    if not rec_dict.get("id"):
        rec_dict["id"] = f"manual-{len(records) + 1}-{int(datetime.datetime.now().timestamp())}"
    records.append(rec_dict)
    save_records(records)

    # 구글 스프레드시트 Web App URL이 설정되어 있다면 즉시 구글 시트에도 새 행으로 적재!
    cfg = load_config()
    webhook_sent = False
    if cfg.get("webhook_url"):
        webhook_sent = append_record_to_google_sheet(cfg["webhook_url"], rec_dict)

    return {
        "status": "success",
        "record": rec_dict,
        "google_sheet_synced": webhook_sent,
        "kpis": calculate_kpis(records)
    }

@app.put("/api/records/{record_id}")
def update_record(record_id: str, record: RecordModel):
    records = load_records()
    found = False
    for i, r in enumerate(records):
        if r.get("id") == record_id:
            updated = record.dict()
            updated["id"] = record_id
            records[i] = updated
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="해당 레코드를 찾을 수 없습니다.")
    save_records(records)
    return {"status": "success", "kpis": calculate_kpis(records)}

@app.delete("/api/records/{record_id}")
def delete_record(record_id: str):
    records = load_records()
    records = [r for r in records if r.get("id") != record_id]
    save_records(records)
    return {"status": "success", "kpis": calculate_kpis(records)}

@app.post("/api/records/reset")
def reset_to_sample():
    if os.path.exists(SAMPLE_FILE):
        with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)
            save_records(records)
            return {"status": "success", "count": len(records), "kpis": calculate_kpis(records)}
    raise HTTPException(status_code=500, detail="샘플 데이터 파일이 없습니다.")

@app.get("/api/google-sheets/config")
def get_gsheet_config():
    return load_config()

@app.post("/api/google-sheets/config")
def update_gsheet_config(req: GoogleSheetConfigRequest):
    cfg = load_config()
    if req.sheet_url is not None:
        cfg["sheet_url"] = req.sheet_url.strip()
    if req.webhook_url is not None:
        cfg["webhook_url"] = req.webhook_url.strip()
    save_config(cfg)
    return {"status": "success", "config": cfg}

@app.get("/api/google-sheets/script-code")
def get_apps_script_code():
    return {"code": get_google_apps_script_code()}

@app.post("/api/google-sheets/sync")
def sync_google_sheets(req: GoogleSheetSyncRequest):
    try:
        new_records, summary = fetch_and_parse_google_sheets(req.url)
        if not new_records:
            raise HTTPException(status_code=400, detail="시트에서 유효한 데이터 행을 찾을 수 없습니다. 헤더와 내용을 확인해 주세요.")

        existing_records = load_records()
        if req.mode == "append":
            combined = existing_records + new_records
        else:
            combined = new_records

        save_records(combined)

        # 설정에 시트 URL 자동 저장
        cfg = load_config()
        cfg["sheet_url"] = req.url
        save_config(cfg)

        return {
            "status": "success",
            "imported_count": len(new_records),
            "total_count": len(combined),
            "summary": summary,
            "kpis": calculate_kpis(combined)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/generate-docx")
def generate_docx():
    records = load_records()
    if not records:
        raise HTTPException(status_code=400, detail="보고서를 생성할 취합 데이터가 없습니다.")

    kpis = calculate_kpis(records)
    ai_analysis = generate_ai_analysis(records, kpis)

    output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
    os.makedirs(output_dir, exist_ok=True)
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    output_filename = f"트릿지_솔루션_활용_성과보고서_{today_str}.docx"
    output_filepath = os.path.join(output_dir, output_filename)

    build_docx_report(records, kpis, ai_analysis, output_filepath)

    return FileResponse(
        path=output_filepath,
        filename=output_filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@app.get("/api/download-template")
def download_template():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    os.makedirs(output_dir, exist_ok=True)
    template_path = os.path.join(output_dir, "트릿지_사용현황_표준취합양식.xlsx")
    generate_google_sheets_template_excel(template_path)
    return FileResponse(
        path=template_path,
        filename="트릿지_사용현황_표준취합양식.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
