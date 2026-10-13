from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import business_data, main, workflow
from app.execution import ApprovalWorker, run_post_approval
from app.models import ProjectRequest
from app.store import ReportStore


@pytest.fixture
def context(monkeypatch):
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_SERVICE_ROLE_KEY', raising=False)
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    monkeypatch.setenv('KNOWLEDGE_RETRIEVAL_MODE', 'local')
    store = ReportStore()
    monkeypatch.setattr(main, 'store', store)
    return store, TestClient(main.app)


def create(store, **changes):
    request = ProjectRequest(customer='Demo customer', project_name='Approved project',
                             brief='Manufacture motorized office roller blinds.', fabric_id='premium_blackout',
                             due_date=date(2099, 1, 1), **changes)
    report = workflow.run_workflow(request)
    assert report['status'] == 'awaiting_review'
    store.save(report)
    return report


def approval():
    return {'reviewer': 'Demo reviewer', 'measurements_confirmed': True, 'specification_confirmed': True,
            'commercial_terms_confirmed': True, 'execution_confirmed': True, 'approved_at': '2026-10-13T12:00:00Z'}


def approve_and_execute(store, report):
    store.approve(report['id'], approval())
    return run_post_approval(store, report['id'])


def test_api_approval_runs_handoffs_and_reserves_without_deducting_stock(context):
    store, client = context
    report = create(store)
    response = client.post(f"/api/projects/{report['id']}/approve", json=approval())
    assert response.status_code == 200
    result = response.json()
    execution = result['execution']
    assert execution['status'] == 'completed'
    assert execution['work_order']['status'] == 'planned'
    assert execution['reservation']['quantity_lm'] == 68.69
    assert len(execution['agent_findings']) == 4
    assert len(execution['tasks']) == 9
    fabric = next(f for f in business_data.load_operations()['fabrics'] if f['id'] == 'premium_blackout')
    assert fabric['on_hand_lm'] == 120
    assert fabric['reserved_lm'] == 68.69
    assert fabric['stock_lm'] == pytest.approx(51.31)
    retry = client.post(f"/api/projects/{report['id']}/approve", json=approval()).json()
    assert retry['execution']['work_order']['id'] == execution['work_order']['id']
    assert retry['execution']['events'] == execution['events']


def test_missing_execution_consent_prevents_approval_and_actions(context):
    store, client = context
    report = create(store)
    response = client.post(f"/api/projects/{report['id']}/approve", json={**approval(), 'execution_confirmed': False})
    assert response.status_code == 422
    assert store.get(report['id'])['status'] == 'awaiting_review'
    assert not store.pending_execution_ids()
    assert client.post(f"/api/projects/{report['id']}/execute").status_code == 409


def test_worker_recovers_queued_approval_after_store_recreation(context):
    store, _ = context
    report = create(store)
    store.approve(report['id'], approval())
    restarted = ReportStore()
    assert restarted.pending_execution_ids() == [report['id']]
    assert ApprovalWorker(restarted).process_once() == 1
    assert restarted.get(report['id'])['execution']['work_order']['status'] == 'planned'
    assert not restarted.pending_execution_ids()


def test_concurrent_approvals_cannot_over_reserve(context):
    store, _ = context
    reports = [create(store), create(store)]
    for report in reports:
        store.approve(report['id'], approval())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda r: run_post_approval(ReportStore(), r['id']), reports))
    assert sorted(r['execution']['status'] for r in results) == ['blocked', 'completed']
    assert sum((r['execution'].get('reservation') or {}).get('quantity_lm', 0) for r in results) == 68.69


def test_cancellation_releases_reservation_and_bookings_and_allows_blocked_retry(context):
    store, _ = context
    first, second = create(store), create(store)
    assert approve_and_execute(store, first)['execution']['status'] == 'completed'
    assert approve_and_execute(store, second)['execution']['status'] == 'blocked'
    cancelled = store.advance(first['id'], 'cancel', 'Demo operator', 'Customer cancelled before production.')
    assert cancelled['execution']['reservation']['status'] == 'released'
    assert all(b['released'] for b in cancelled['execution']['bookings'])
    assert run_post_approval(store, second['id'])['execution']['status'] == 'completed'
    assert run_post_approval(store, first['id'])['execution']['status'] == 'cancelled'


def test_progress_gates_quality_and_consumes_material_exactly_once(context):
    store, client = context
    report = approve_and_execute(store, create(store, quantity=4))
    id = report['id']
    endpoint = f'/api/projects/{id}/work-order/actions'
    assert client.post(endpoint, json={'action': 'pass_quality', 'actor': 'QA operator'}).status_code == 409
    store.advance(id, 'start_production', 'Factory operator')
    result = store.advance(id, 'finish_production', 'Factory operator')
    assert result['execution']['reservation']['status'] == 'consumed'
    before = business_data.load_operations()
    store.advance(id, 'finish_production', 'Factory operator')
    assert business_data.load_operations()['fabrics'] == before['fabrics']
    assert client.post(endpoint, json={'action': 'pass_quality', 'actor': 'QA operator'}).status_code == 409
    failed = store.advance(id, 'fail_quality', 'QA operator', 'Alignment requires correction.')
    assert all(t['status'] == 'failed' for t in failed['execution']['tasks'] if t['stage'] == 'quality')
    checks = [t['id'] for t in failed['execution']['tasks'] if t['stage'] == 'quality']
    ready = store.advance(id, 'pass_quality', 'QA operator', 'Checks repeated after correction.', checks)
    assert ready['execution']['work_order']['status'] == 'ready_for_installation'
    complete = store.advance(id, 'complete_installation', 'Site operator', 'Handover recorded.')
    assert complete['execution']['work_order']['status'] == 'completed'
    assert all(t['status'] == 'completed' for t in complete['execution']['tasks'])


def test_cancel_after_manufacturing_does_not_restore_consumed_material(context):
    store, _ = context
    report = approve_and_execute(store, create(store, quantity=4))
    id = report['id']
    store.advance(id, 'start_production', 'Operator')
    with pytest.raises(ValueError):
        store.advance(id, 'cancel', 'Operator', 'Cancel during production.')
    store.advance(id, 'finish_production', 'Operator')
    fabric_before = next(f for f in business_data.load_operations()['fabrics'] if f['id'] == 'premium_blackout')
    result = store.advance(id, 'cancel', 'Operator', 'Installation cancelled after manufacturing.')
    fabric_after = next(f for f in business_data.load_operations()['fabrics'] if f['id'] == 'premium_blackout')
    assert fabric_before['on_hand_lm'] == fabric_after['on_hand_lm']
    assert result['execution']['reservation']['status'] == 'consumed'
    assert all(not b['released'] for b in result['execution']['bookings'] if b['stage'] == 'factory')


def test_local_bookings_share_capacity_without_overbooking(context):
    store, _ = context
    reports = [approve_and_execute(store, create(store, quantity=10)) for _ in range(3)]
    totals = {}
    for report in reports:
        for b in report['execution']['bookings']:
            key = (b['stage'], b['work_date'])
            totals[key] = totals.get(key, 0) + b['hours']
    assert max(totals.values()) <= 6


def test_local_write_failure_leaves_approval_and_queue_unchanged(context, monkeypatch):
    from app.store import StorageUnavailable
    store, _ = context
    report = create(store)
    def failed_write(data):
        raise OSError('Test disk failure')
    monkeypatch.setattr(store, '_write', failed_write)
    with pytest.raises(StorageUnavailable):
        store.approve(report['id'], approval())
    restarted = ReportStore()
    assert restarted.get(report['id'])['status'] == 'awaiting_review'
    assert not restarted.pending_execution_ids()


def test_failed_queued_job_does_not_block_other_jobs(context, monkeypatch):
    from app import execution
    store, _ = context
    first, second = create(store, quantity=4), create(store, quantity=4)
    for report in (first, second):
        store.approve(report['id'], approval())
    original = execution.run_post_approval
    def interrupted(store, report_id):
        if report_id == first['id']:
            raise RuntimeError('One job temporarily fails')
        return original(store, report_id)
    monkeypatch.setattr(execution, 'run_post_approval', interrupted)
    assert ApprovalWorker(store).process_once() == 1
    assert store.get(first['id'])['execution']['status'] == 'queued'
    assert store.get(second['id'])['execution']['status'] == 'completed'
