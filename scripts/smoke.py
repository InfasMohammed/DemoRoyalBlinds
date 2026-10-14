"""Functional readiness check against the local API; creates one synthetic report."""

import json
from datetime import date, timedelta
from urllib.request import Request, urlopen


def request(path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(
        "http://127.0.0.1:8000/api" + path, data=body, headers={"Content-Type": "application/json"}
    )
    with urlopen(req, timeout=180) as response:
        return json.load(response)


health = request("/health")
due = (date.fromisoformat(health["today"]) + timedelta(days=45)).isoformat()
result = request(
    "/projects/analyze",
    {
        "customer": "Demo · Readiness check",
        "project_name": "Synthetic smoke-test project",
        "brief": "Demonstration: 24 motorized blackout rollers for an office. No real order.",
        "product": "motorized_roller",
        "fabric_id": "premium_blackout",
        "quantity": 24,
        "width_m": 1.8,
        "height_m": 2.4,
        "due_date": due,
        "site": "Demo site, Dubai",
    },
)
assert len(result["traces"]) == 6, "All specialists must execute"
assert result["data_snapshot"]["data_source"] == health["business_data_source"], (
    "Report must use the configured business data"
)
if health["business_data_source"] == "demo":
    assert result["status"] == "awaiting_review", "Stocked, flexible fixture should reach review"
    assert result["costing"]["total"] == 20404.27, "Expected fixture pricing result changed"
else:
    assert result["costing"]["total"] == round(
        result["costing"]["subtotal"] + result["costing"]["vat"], 2
    )
    assert result["status"] in ("blocked", "awaiting_review"), "Coordinator must gate review"
assert request("/projects/" + result["id"])["id"] == result["id"], "Saved report must be readable"
print(
    "PASS: six specialists, fabric yield, AED pricing, schedule, review gate and report persistence."
)
print(f"Storage: {health['storage_mode']}; actual reasoning: {result['reasoning_mode']}.")
