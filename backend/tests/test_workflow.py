from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import main, workflow
from app.models import ProjectRequest
from app.store import ReportStore


@pytest.fixture(autouse=True)
def demo_context(monkeypatch, tmp_path):
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_SERVICE_ROLE_KEY', raising=False)
    monkeypatch.setenv('DEMO_STORE_PATH', str(tmp_path / 'reports.json'))
    monkeypatch.setattr(workflow, 'today', lambda: date(2026, 10, 13))
    monkeypatch.setattr(main, 'today', lambda: date(2026, 10, 13))
    monkeypatch.setattr(main, 'store', ReportStore())


def project(**changes):
    return ProjectRequest(customer='Demo Customer', project_name='Office fit-out',
                          brief='24 motorized blackout blinds for office windows.',
                          due_date=date(2026, 11, 30), **changes)


def test_shortage_has_evidence_and_blocks_approval():
    result = workflow.run_workflow(project())
    assert result['materials']['required_lm'] == 68.69
    assert result['materials']['shortage_lm'] == 40.69
    assert result['materials']['alternatives'][0]['id'] == 'premium_blackout'
    assert result['status'] == 'blocked'
    assert len(result['traces']) == 6
    assert all(t['sources'] and t['mode'] == 'rules' for t in result['traces'])
    assert result['reasoning_mode'] == 'rule_based_demo'


def test_stocked_order_price_and_schedule():
    result = workflow.run_workflow(project(fabric_id='premium_blackout'))
    assert result['status'] == 'awaiting_review'
    assert result['materials']['in_stock']
    assert result['production']['manufacture_start'] == '2026-10-15'
    assert result['production']['manufacture_end'] == '2026-10-19'
    assert result['production']['quality_date'] == '2026-10-20'
    assert result['production']['completion_date'] == '2026-10-22'
    costs = result['costing']
    assert costs['direct_cost'] == 13602.85
    assert costs['subtotal'] == 19432.64
    assert costs['vat'] == 971.63
    assert costs['total'] == 20404.27


def test_rush_order_blocks_even_if_material_available():
    req = project(fabric_id='premium_blackout')
    req.due_date = date(2026, 10, 18)
    result = workflow.run_workflow(req)
    assert not result['production']['on_time']
    assert result['status'] == 'blocked'
    assert len(result['decision']['blockers']) == 1


@pytest.mark.parametrize('changes,fragment', [
    ({'width_m': 3.5}, 'Dimensions exceed'),
    ({'product': 'curtain', 'fabric_id': 'solar_screen'}, 'incompatible'),
    ({'width_m': 3.0, 'fabric_id': 'solar_screen'}, 'exceeds roll width'),
])
def test_unsupported_specs_block_quote(changes, fragment):
    result = workflow.run_workflow(project(**changes))
    assert not result['costing']['valid']
    assert any(fragment in item for item in result['quality']['blockers'])


def test_narrow_panels_share_roll_rows():
    result = workflow.run_workflow(project(width_m=1.4, fabric_id='premium_blackout'))
    assert result['materials']['required_lm'] == 34.34


def test_curtain_fullness_uses_whole_drops():
    result = workflow.run_workflow(project(product='curtain', quantity=10, width_m=2.0, height_m=2.4, fabric_id='premium_blackout'))
    assert result['materials']['required_lm'] == 58.32
    assert 'Motor & remote sets' not in [line['description'] for line in result['costing']['lines']]
    assert result['status'] == 'awaiting_review'


def test_weekend_calendar():
    assert workflow.business_day_on_or_after(date(2026, 10, 17)) == date(2026, 10, 19)
    assert workflow.add_business_days(date(2026, 10, 16), 1) == date(2026, 10, 19)


def test_complete_api_review_flow():
    client = TestClient(main.app)
    response = client.post('/api/projects/analyze', json=project(fabric_id='premium_blackout').model_dump(mode='json'))
    assert response.status_code == 201
    report = response.json()
    report_id = report['id']
    assert client.get('/api/projects').json()[0]['id'] == report_id
    assert client.get(f'/api/projects/{report_id}').json()['status'] == 'awaiting_review'
    approval = {'reviewer': 'Demo reviewer', 'measurements_confirmed': True,
                'specification_confirmed': True, 'commercial_terms_confirmed': True}
    assert client.post(f'/api/projects/{report_id}/approve', json={**approval, 'measurements_confirmed': False}).status_code == 422
    response = client.post(f'/api/projects/{report_id}/approve', json=approval)
    assert response.status_code == 200
    assert response.json()['status'] == 'demo_approved'
    assert client.get(f'/api/projects/{report_id}').json()['approval']['reviewer'] == 'Demo reviewer'
    assert client.post(f'/api/projects/{report_id}/approve', json=approval).status_code == 409
    assert client.get('/api/projects/not-found').status_code == 404


def test_cannot_approve_blocked_report():
    client = TestClient(main.app)
    report = client.post('/api/projects/analyze', json=project().model_dump(mode='json')).json()
    response = client.post(f"/api/projects/{report['id']}/approve", json={
        'reviewer': 'Demo reviewer', 'measurements_confirmed': True,
        'specification_confirmed': True, 'commercial_terms_confirmed': True})
    assert response.status_code == 409
    assert main.store.get(report['id'])['status'] == 'blocked'


def test_invalid_inputs_and_past_deadline_rejected():
    client = TestClient(main.app)
    req = project().model_dump(mode='json')
    assert client.post('/api/projects/analyze', json={**req, 'quantity': 0}).status_code == 422
    assert client.post('/api/projects/analyze', json={**req, 'width_m': -1}).status_code == 422
    assert client.post('/api/projects/analyze', json={**req, 'due_date': '2026-10-01'}).status_code == 422


def test_ai_outage_is_visible_and_does_not_change_rules(monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', 'test-placeholder')

    def unavailable(**kwargs):
        raise RuntimeError('Provider unavailable')

    monkeypatch.setattr(workflow, 'ChatOpenAI', unavailable)
    result = workflow.run_workflow(project())
    assert result['reasoning_mode'] == 'ai_with_fallback'
    assert all(trace['mode'] == 'rules_fallback' for trace in result['traces'])
    assert result['status'] == 'blocked'


def test_partial_supabase_configuration_fails_explicitly(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    with pytest.raises(RuntimeError, match='both'):
        ReportStore()


@pytest.mark.parametrize('key', ['sb_secret_not_a_real_key', 'proxy-placeholder-not-a-real-key'])
def test_supabase_client_accepts_server_keys_and_proxy_bindings(monkeypatch, key):
    """Regression: older SDKs rejected these formats before making a request."""
    import httpx

    def no_network(*args, **kwargs):
        raise AssertionError('Client initialization must not make a network request')

    monkeypatch.setattr(httpx.Client, 'send', no_network)
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', key)
    store = ReportStore()
    assert store.mode == 'supabase'
    assert store.client.table('demo_reports') is not None


def test_local_storage_survives_store_recreation():
    report = workflow.run_workflow(project())
    first = ReportStore()
    first.save(report)
    second = ReportStore()
    assert second.get(report['id']) == report
