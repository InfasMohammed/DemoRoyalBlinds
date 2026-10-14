"""Offline counterpart of the transactional Supabase tools (one JSON file).

ReportStore holds the shared local lock and writes the complete result once.
Database mode never invokes this module for action storage.
"""

import copy
import json
from datetime import date, datetime, timezone
from uuid import uuid4

from .business_data import DATA_DIR, Operations
from .clock import today
from .workflow import add_business_days, business_day_on_or_after


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def event(report, kind, actor, detail):
    execution = report["execution"]
    execution["events"].append(
        {
            "id": len(execution["events"]) + 1,
            "event_type": kind,
            "actor": actor,
            "detail": detail,
            "created_at": timestamp(),
        }
    )
    execution["updated_at"] = timestamp()


def queue_approval(report, approval):
    if report["status"] == "demo_approved":
        return
    if report["status"] != "awaiting_review":
        raise ValueError("This report has unresolved blockers.")
    if not all(
        approval.get(key)
        for key in (
            "measurements_confirmed",
            "specification_confirmed",
            "commercial_terms_confirmed",
            "execution_confirmed",
        )
    ):
        raise ValueError("All review and execution confirmations are required.")
    report.update(
        status="demo_approved",
        approval=approval,
        execution={
            "status": "queued",
            "reason": None,
            "work_order": None,
            "reservation": None,
            "tasks": [],
            "bookings": [],
            "events": [],
            "agent_findings": [],
            "updated_at": timestamp(),
        },
    )
    event(
        report,
        "quotation_approved",
        approval["reviewer"],
        "Quotation approved; demo execution authorized and queued.",
    )


def raw_operations():
    return Operations.model_validate(
        json.loads((DATA_DIR / "demo_operations.json").read_text())
    ).model_dump(mode="json")


def material_totals(data, material_id):
    consumed = reserved = 0
    for report in data.values():
        reservation = (report.get("execution") or {}).get("reservation")
        if reservation and reservation["material_id"] == material_id:
            if reservation["status"] == "active":
                reserved += reservation["quantity_lm"]
            elif reservation["status"] == "consumed":
                consumed += reservation["quantity_lm"]
    return round(consumed, 2), round(reserved, 2)


def book_hours(existing, created, order_id, stage, start, hours, capacity, policy, deadline):
    calendar = (policy["working_weekdays"], policy["holidays"])
    day = business_day_on_or_after(start, *calendar)
    remaining = hours
    while remaining > 0:
        if day > deadline:
            raise ValueError(
                "Existing bookings leave insufficient capacity before the requested deadline."
            )
        taken = sum(
            b["hours"]
            for b in existing
            if b["stage"] == stage and b["work_date"] == day.isoformat() and not b["released"]
        )
        free = max(0, round(capacity - taken, 4))
        if free:
            allocated = min(remaining, free)
            created.append(
                {
                    "work_order_id": order_id,
                    "stage": stage,
                    "work_date": day.isoformat(),
                    "hours": allocated,
                    "released": False,
                }
            )
            remaining = round(remaining - allocated, 4)
        if remaining:
            day = add_business_days(day, 1, *calendar)
    return day


def execute_local(data, report, plan, findings):
    execution = report.get("execution")
    if not execution:
        raise ValueError(
            "This approval predates the execution workflow. Analyze and approve a new report."
        )
    if execution["status"] in ("completed", "cancelled"):
        return
    if report["status"] != "demo_approved" or not report.get("approval", {}).get(
        "execution_confirmed"
    ):
        raise ValueError("Human approval and execution authorization are required.")
    ops = raw_operations()
    snapshot = report.get("data_snapshot")
    req = report["request"]
    reason = None
    material = next((f for f in ops["fabrics"] if f["id"] == req["fabric_id"]), None)
    product = ops["products"].get(req["product"])
    if not snapshot or snapshot["data_source"] != "demo":
        reason = "Analyze a new quotation using offline business data before execution."
    elif not product or not material:
        reason = "The approved material or product is missing or invalid."
    elif (
        product != snapshot["products"][req["product"]]
        or ops["policy"] != snapshot["policy"]
        or ops["checklists"][req["product"]] != snapshot["checklists"][req["product"]]
    ):
        reason = "Product specifications, rates or planning settings changed. Analyze and approve a fresh quotation."
    elif any(
        material[k] != report["materials"]["fabric"][k]
        for k in material
        if k not in ("stock_lm", "on_hand_lm", "reserved_lm")
    ):
        reason = "Material specifications or prices changed. Analyze and approve a fresh quotation."
    else:
        consumed, reserved = material_totals(data, material["id"])
        if (
            round(material["stock_lm"] - consumed - reserved, 2)
            < report["materials"]["required_lm"]
        ):
            reason = "Available material is insufficient after existing reservations. Replenish or approve a revised specification."
    bookings = []
    final_plan = copy.deepcopy(plan)
    order_id = str(uuid4())
    if not reason:
        policy = ops["policy"]
        calendar = (policy["working_weekdays"], policy["holidays"])
        existing = [
            b for r in data.values() for b in (r.get("execution") or {}).get("bookings", [])
        ]
        try:
            start = max(
                date.fromisoformat(plan["manufacture_start"]),
                add_business_days(today(), policy["queue_business_days"], *calendar),
            )
            deadline = date.fromisoformat(req["due_date"])
            factory_end = book_hours(
                existing,
                bookings,
                order_id,
                "factory",
                start,
                plan["factory_hours"],
                policy["factory_hours_day"],
                policy,
                deadline,
            )
            quality_day = add_business_days(factory_end, policy["quality_business_days"], *calendar)
            install_end = book_hours(
                existing,
                bookings,
                order_id,
                "installation",
                add_business_days(quality_day, 1, *calendar),
                plan["installation_hours"],
                policy["installation_hours_day"],
                policy,
                deadline,
            )
            final_plan.update(
                manufacture_start=min(b["work_date"] for b in bookings if b["stage"] == "factory"),
                manufacture_end=factory_end.isoformat(),
                quality_date=quality_day.isoformat(),
                installation_start=min(
                    b["work_date"] for b in bookings if b["stage"] == "installation"
                ),
                completion_date=install_end.isoformat(),
                on_time=True,
                slack_days=(deadline - install_end).days,
            )
        except ValueError as exc:
            reason = str(exc)
    execution["agent_findings"] = findings
    if reason:
        if execution["status"] != "blocked" or execution["reason"] != reason:
            event(report, "execution_blocked", "Post-approval workflow", reason)
        execution.update(status="blocked", reason=reason)
        return
    tasks = []
    for stage, descriptions in [
        ("manufacturing", ["Manufacture the approved openings and record finished dimensions."]),
        ("quality", ops["checklists"][req["product"]]),
        ("installation", ["Install at the approved site and record customer handover."]),
    ]:
        tasks.extend(
            {
                "id": str(uuid4()),
                "work_order_id": order_id,
                "stage": stage,
                "description": d,
                "status": "pending",
            }
            for d in descriptions
        )
    execution.update(
        status="completed",
        reason=None,
        work_order={
            "id": order_id,
            "report_id": report["id"],
            "status": "planned",
            "production_plan": final_plan,
            "created_at": timestamp(),
        },
        reservation={
            "report_id": report["id"],
            "material_id": req["fabric_id"],
            "quantity_lm": report["materials"]["required_lm"],
            "status": "active",
            "created_at": timestamp(),
        },
        bookings=bookings,
        tasks=tasks,
    )
    event(
        report,
        "work_order_created",
        "Post-approval workflow",
        "Material reserved; capacity booked; manufacturing, quality and installation tasks created.",
    )


def advance_local(data, report, action, actor, note, checked_ids):
    execution = report.get("execution") or {}
    order = execution.get("work_order")
    if not order:
        raise ValueError("No work order is ready. Resolve execution blockers first.")
    if len(actor.strip()) < 2:
        raise ValueError("An operator name is required.")
    status = order["status"]
    already = {
        "start_production": (
            "in_production",
            "awaiting_quality",
            "ready_for_installation",
            "completed",
        ),
        "finish_production": ("awaiting_quality", "ready_for_installation", "completed"),
        "pass_quality": ("ready_for_installation", "completed"),
        "complete_installation": ("completed",),
        "cancel": ("cancelled",),
    }
    if status in already.get(action, ()):
        return
    tasks = execution["tasks"]
    reservation = execution["reservation"]
    material = next(f for f in raw_operations()["fabrics"] if f["id"] == reservation["material_id"])
    consumed, reserved = material_totals(data, material["id"])
    new_status = None
    if action == "start_production" and status == "planned":
        if material["stock_lm"] - consumed < reserved:
            raise ValueError(
                "Recorded stock is below active reservations. Reconcile stock before production."
            )
        new_status = "in_production"
        for t in tasks:
            if t["stage"] == "manufacturing":
                t["status"] = "in_progress"
    elif action == "finish_production" and status == "in_production":
        if (
            reservation["status"] != "active"
            or round(material["stock_lm"] - consumed, 2) < reserved
        ):
            raise ValueError("Material reservation cannot be consumed. Reconcile stock first.")
        reservation["status"] = "consumed"
        for t in tasks:
            if t["stage"] == "manufacturing":
                t["status"] = "completed"
        new_status = "awaiting_quality"
    elif action == "pass_quality" and status == "awaiting_quality":
        required = {t["id"] for t in tasks if t["stage"] == "quality"}
        if set(checked_ids) != required:
            raise ValueError(
                "Every quality check must be confirmed; only current quality check IDs are accepted."
            )
        for t in tasks:
            if t["stage"] == "quality":
                t["status"] = "completed"
        new_status = "ready_for_installation"
    elif action == "fail_quality" and status == "awaiting_quality":
        if len(note.strip()) < 5:
            raise ValueError("Record the quality issue before placing a hold.")
        for t in tasks:
            if t["stage"] == "quality":
                t["status"] = "failed"
        new_status = status
    elif action == "complete_installation" and status == "ready_for_installation":
        for t in tasks:
            if t["stage"] == "installation":
                t["status"] = "completed"
        new_status = "completed"
    elif action == "cancel" and status in ("planned", "awaiting_quality", "ready_for_installation"):
        if len(note.strip()) < 5:
            raise ValueError("Record a cancellation reason.")
        was_active = reservation["status"] == "active"
        if was_active:
            reservation["status"] = "released"
        for b in execution["bookings"]:
            if was_active or b["stage"] == "installation":
                b["released"] = True
        for t in tasks:
            if t["status"] != "completed":
                t["status"] = "cancelled"
        execution["status"] = new_status = "cancelled"
    else:
        raise ValueError("This action does not match the current work-order stage.")
    order["status"] = new_status
    event(report, action, actor, note)
