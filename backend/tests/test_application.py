"""Application composition and worker lifecycle regressions."""

import pytest
from fastapi.testclient import TestClient

from app import main


def test_application_instances_use_their_own_report_store(monkeypatch):
    class Store:
        def __init__(self, report_id):
            self.report_id = report_id

        def list(self):
            return [{"id": self.report_id}]

    stores = iter([Store("first"), Store("second")])
    monkeypatch.setattr(main, "ReportStore", lambda: next(stores))
    first = main.create_app()
    second = main.create_app()

    assert first.state.report_store is not second.state.report_store
    assert TestClient(first).get("/api/projects").json() == [{"id": "first"}]
    assert TestClient(second).get("/api/projects").json() == [{"id": "second"}]


def test_worker_stops_when_application_context_raises(monkeypatch):
    events = []

    class Worker:
        def __init__(self, store):
            self.store = store

        def start(self):
            events.append("started")

        def stop(self):
            events.append("stopped")

    monkeypatch.setattr(main, "ApprovalWorker", Worker)
    monkeypatch.setenv("POST_APPROVAL_WORKER_ENABLED", "true")
    with pytest.raises(RuntimeError, match="interrupted"):
        with TestClient(main.create_app()):
            assert events == ["started"]
            raise RuntimeError("interrupted")
    assert events == ["started", "stopped"]
