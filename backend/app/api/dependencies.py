from fastapi import Request

from ..store import ReportStore


def get_report_store(request: Request) -> ReportStore:
    """Each application instance owns its persistence and approval queue."""
    return request.app.state.report_store
