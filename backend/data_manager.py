import json
import os
from typing import List, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
STORAGE_FILE = os.path.join(DATA_DIR, "current_records.json")
SAMPLE_FILE = os.path.join(os.path.dirname(__file__), "sample_data.json")

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

def load_records() -> List[Dict[str, Any]]:
    ensure_data_dir()
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # 기본 샘플 데이터 로드
    if os.path.exists(SAMPLE_FILE):
        with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)
            save_records(records)
            return records
    return []

def save_records(records: List[Dict[str, Any]]):
    ensure_data_dir()
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def calculate_kpis(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    취합된 레코드로부터 경영진 보고용 종합 KPI를 산출합니다.
    """
    if not records:
        return {
            "total_count": 0,
            "department_count": 0,
            "solution_breakdown": {},
            "status_breakdown": {},
            "total_db_count": 0,
            "total_actions": 0,
            "total_financial_impact": 0.0,
            "total_time_saved": 0.0,
            "avg_satisfaction": 0.0,
            "departments": []
        }

    departments = sorted(list(set(r.get("department", "기타") for r in records)))
    total_count = len(records)
    
    solution_counts = {}
    status_counts = {}
    total_db = 0
    total_actions = 0
    total_financial = 0.0
    total_time = 0.0
    satisfaction_sum = 0.0

    for r in records:
        sol = r.get("solution", "기타")
        solution_counts[sol] = solution_counts.get(sol, 0) + 1

        stat = r.get("status", "진행중")
        status_counts[stat] = status_counts.get(stat, 0) + 1

        total_db += int(r.get("valid_db_count", 0))
        total_actions += int(r.get("action_count", 0))
        total_financial += float(r.get("financial_impact", 0.0))
        total_time += float(r.get("time_saved_hours", 0.0))
        satisfaction_sum += float(r.get("satisfaction", 4))

    avg_sat = round(satisfaction_sum / total_count, 1) if total_count > 0 else 0.0

    return {
        "total_count": total_count,
        "department_count": len(departments),
        "solution_breakdown": solution_counts,
        "status_breakdown": status_counts,
        "total_db_count": total_db,
        "total_actions": total_actions,
        "total_financial_impact": round(total_financial, 1),
        "total_time_saved": round(total_time, 1),
        "avg_satisfaction": avg_sat,
        "departments": departments
    }
