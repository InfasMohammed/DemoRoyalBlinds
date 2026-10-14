from fastapi import APIRouter, Depends

from ..business_data import load_operations
from ..clock import today
from ..llm import chat_info
from ..store import ReportStore
from ..workflow import llm_enabled
from .dependencies import get_report_store

router = APIRouter(tags=["health"])


@router.get("/health")
def health(store: ReportStore = Depends(get_report_store)):
    business = load_operations()
    return {
        "status": "ok",
        "storage_mode": store.mode,
        "reasoning_mode": "live_ai_configured" if llm_enabled() else "rule_based_demo",
        "data_mode": "synthetic_demo" if business["is_sample"] else "configured_records",
        "today": today().isoformat(),
        "chat_provider": chat_info(),
        "business_data_source": business["data_source"],
        "business_data_fetched_at": business["fetched_at"],
    }
