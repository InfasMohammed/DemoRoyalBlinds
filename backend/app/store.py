"""Persist reports and execute bounded demo actions through atomic tools."""

import json
import os
import threading
from pathlib import Path
from typing import Any

from postgrest.exceptions import APIError
from supabase import create_client


class StorageUnavailable(RuntimeError):
    pass


LOCAL_LOCK = threading.RLock()


def local_store_path():
    return Path(
        os.getenv(
            "DEMO_STORE_PATH",
            str(Path(__file__).resolve().parents[2] / ".runtime" / "reports.json"),
        )
    )


class ReportStore:
    def __init__(self):
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if bool(url) != bool(key):
            raise RuntimeError(
                "Configure both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY, or leave both unset."
            )
        self.client = create_client(url, key) if url and key else None
        self.mode = "supabase" if self.client else "local_demo"
        self.path = local_store_path()
        self.lock = LOCAL_LOCK

    def _read(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def _write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2))
        temporary.replace(self.path)

    def save(self, report: dict[str, Any]):
        try:
            if self.client:
                self.client.table("demo_reports").insert(
                    {
                        "id": report["id"],
                        "project_name": report["request"]["project_name"],
                        "status": report["status"],
                        "payload": report,
                    }
                ).execute()
            else:
                with self.lock:
                    data = self._read()
                    data[report["id"]] = report
                    self._write(data)
        except Exception as exc:
            raise StorageUnavailable(
                "Could not save the report. Check database setup and connection."
            ) from exc

    def list(self):
        try:
            if self.client:
                return [
                    row["payload"]
                    for row in self.client.table("demo_reports")
                    .select("payload")
                    .order("created_at", desc=True)
                    .limit(50)
                    .execute()
                    .data
                ]
            with self.lock:
                return sorted(
                    self._read().values(), key=lambda item: item["created_at"], reverse=True
                )[:50]
        except Exception as exc:
            raise StorageUnavailable(
                "Could not load reports. Check database setup and connection."
            ) from exc

    def get(self, report_id):
        try:
            if self.client:
                rows = (
                    self.client.table("demo_reports")
                    .select("payload")
                    .eq("id", report_id)
                    .execute()
                    .data
                )
                return rows[0]["payload"] if rows else None
            with self.lock:
                return self._read().get(report_id)
        except Exception as exc:
            raise StorageUnavailable(
                "Could not load the report. Check database setup and connection."
            ) from exc

    def _rpc(self, function, arguments):
        try:
            return self.client.rpc(function, arguments).execute().data
        except APIError as exc:
            if exc.code == "P0001":
                raise ValueError(exc.message) from exc
            raise StorageUnavailable(
                "Post-approval database action unavailable. Apply supabase/post_approval.sql and check the connection. Pending actions can be retried."
            ) from exc
        except Exception as exc:
            raise StorageUnavailable(
                "Post-approval database action unavailable. Apply supabase/post_approval.sql and check the connection. Pending actions can be retried."
            ) from exc

    def _local_action(self, report_id, operation):
        try:
            with self.lock:
                data = self._read()
                report = data.get(report_id)
                if not report:
                    return None
                operation(data, report)
                self._write(data)
                return report
        except ValueError:
            raise
        except Exception as exc:
            raise StorageUnavailable(
                "Could not persist the demo action. Reload the report before retrying."
            ) from exc

    def approve(self, report_id, approval):
        """Approval + durable job are written atomically; repeat requests are safe."""
        if self.client:
            return self._rpc("approve_project", {"p_report_id": report_id, "p_approval": approval})
        from .local_execution import queue_approval

        return self._local_action(report_id, lambda data, report: queue_approval(report, approval))

    def execute(self, report_id, plan, findings):
        if self.client:
            return self._rpc(
                "execute_approved_project",
                {"p_report_id": report_id, "p_plan": plan, "p_findings": findings},
            )
        from .local_execution import execute_local

        return self._local_action(
            report_id, lambda data, report: execute_local(data, report, plan, findings)
        )

    def advance(self, report_id, action, actor, note="", checked_ids=None):
        if self.client:
            return self._rpc(
                "advance_work_order",
                {
                    "p_report_id": report_id,
                    "p_action": action,
                    "p_actor": actor,
                    "p_note": note,
                    "p_checked_ids": checked_ids or [],
                },
            )
        from .local_execution import advance_local

        return self._local_action(
            report_id,
            lambda data, report: advance_local(
                data, report, action, actor, note, checked_ids or []
            ),
        )

    def pending_execution_ids(self):
        try:
            if self.client:
                rows = (
                    self.client.table("approval_jobs")
                    .select("report_id")
                    .eq("status", "queued")
                    .limit(10)
                    .execute()
                    .data
                )
                return [r["report_id"] for r in rows]
            with self.lock:
                return [
                    r["id"]
                    for r in self._read().values()
                    if (r.get("execution") or {}).get("status") == "queued"
                ][:10]
        except Exception as exc:
            raise StorageUnavailable("Could not read the post-approval queue.") from exc
