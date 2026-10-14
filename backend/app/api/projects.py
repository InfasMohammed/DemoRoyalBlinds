from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..access import Reviewer, require_reviewer
from ..clock import today
from ..execution import run_post_approval
from ..models import ApprovalRequest, ProjectRequest, WorkOrderAction
from ..store import ReportStore
from ..workflow import run_workflow
from .dependencies import get_report_store

router = APIRouter(tags=["projects"])


@router.post("/projects/analyze", status_code=201)
def analyze(
    request: ProjectRequest,
    store: ReportStore = Depends(get_report_store),
    reviewer: Reviewer | None = Depends(require_reviewer),
):
    if request.due_date < today():
        raise HTTPException(422, "Requested completion date must be today or later.")
    try:
        report = run_workflow(request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if reviewer:
        report["created_by"] = {"user_id": reviewer.user_id, "email": reviewer.email}
    store.save(report)
    return report


@router.get("/projects")
def projects(store: ReportStore = Depends(get_report_store)):
    return store.list()


@router.get("/projects/{report_id}")
def project(report_id: str, store: ReportStore = Depends(get_report_store)):
    report = store.get(report_id)
    if not report:
        raise HTTPException(404, "Project report not found.")
    return report


@router.post("/projects/{report_id}/approve")
def approve(
    report_id: str,
    request: ApprovalRequest,
    store: ReportStore = Depends(get_report_store),
    reviewer: Reviewer | None = Depends(require_reviewer),
):
    if not all(
        [
            request.measurements_confirmed,
            request.specification_confirmed,
            request.commercial_terms_confirmed,
            request.execution_confirmed,
        ]
    ):
        raise HTTPException(
            422, "All review confirmations and demo execution authorization are required."
        )
    identity = (
        {"approved_by_user_id": reviewer.user_id, "approved_by_email": reviewer.email}
        if reviewer
        else {}
    )
    try:
        report = store.approve(
            report_id,
            {
                **request.model_dump(),
                **identity,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "scope": "Approve quotation, reserve demo material and create a demo work order.",
            },
        )
        if report:
            report = run_post_approval(store, report_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if not report:
        raise HTTPException(404, "Project report not found.")
    return report


@router.post("/projects/{report_id}/execute")
def retry_execution(report_id: str, store: ReportStore = Depends(get_report_store)):
    try:
        report = run_post_approval(store, report_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if not report:
        raise HTTPException(404, "Project report not found.")
    return report


@router.post("/projects/{report_id}/work-order/actions")
def work_order_action(
    report_id: str,
    request: WorkOrderAction,
    store: ReportStore = Depends(get_report_store),
    reviewer: Reviewer | None = Depends(require_reviewer),
):
    try:
        values = request.model_dump(mode="json")
        if reviewer:
            values["actor"] = reviewer.email
        report = store.advance(report_id, **values)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if not report:
        raise HTTPException(404, "Project report not found.")
    return report
