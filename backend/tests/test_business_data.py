import copy
import json
from datetime import date
from types import SimpleNamespace

import pytest
import httpx
from fastapi.testclient import TestClient
from supabase import create_client as real_create_client
from supabase.lib.client_options import SyncClientOptions

from app import business_data, knowledge, main, workflow
from app.models import ProjectRequest


@pytest.fixture
def database(monkeypatch):
    ops = business_data.load_operations()
    corpus = knowledge.load_corpus()
    metadata = {k: v for k, v in corpus.items() if k not in ('products', 'documents', 'chunks', 'data_source')}
    rows = {'get_operations_snapshot': copy.deepcopy(ops),
            'get_company_knowledge_snapshot': {'products': copy.deepcopy(corpus['products']),
                                               'chunks': copy.deepcopy(corpus['chunks']), 'metadata': metadata}}
    calls = []

    class Client:
        def rpc(self, function, arguments):
            assert arguments == {}
            calls.append(function)
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=copy.deepcopy(rows[function])))

    monkeypatch.setenv('BUSINESS_DATA_SOURCE', 'supabase')
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'fake-server-key')
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    monkeypatch.setenv('KNOWLEDGE_RETRIEVAL_MODE', 'local')
    monkeypatch.setattr(business_data, 'create_client', lambda *args: Client())
    monkeypatch.setattr(workflow, 'today', lambda: date(2026, 10, 13))
    return rows, calls


def project(**changes):
    return ProjectRequest(customer='Demo customer', project_name='Database workflow',
                          brief='Manufacture 24 motorized roller blinds.',
                          due_date=date(2099, 1, 1), **changes)


def test_auto_uses_supabase_when_both_credentials_exist(database, monkeypatch):
    monkeypatch.setenv('BUSINESS_DATA_SOURCE', 'auto')
    assert business_data.load_operations()['data_source'] == 'supabase'


def test_database_stock_change_changes_decision_and_keeps_historical_snapshot(database):
    rows, calls = database
    first = workflow.run_workflow(project())
    assert first['status'] == 'blocked'
    fabric = next(f for f in rows['get_operations_snapshot']['fabrics'] if f['id'] == 'linen_blackout')
    fabric['stock_lm'] = 200
    second = workflow.run_workflow(project())
    assert second['status'] == 'awaiting_review'
    assert second['materials']['fabric']['stock_lm'] == 200
    assert first['materials']['fabric']['stock_lm'] == 28
    assert all(t['data_source'] == 'supabase' for t in second['traces'])
    assert calls.count('get_operations_snapshot') == 2
    assert calls.count('get_company_knowledge_snapshot') == 2


def test_database_rules_rates_checklist_and_calendar_are_used(database):
    rows, _ = database
    ops = rows['get_operations_snapshot']
    product = ops['products']['motorized_roller']
    product.update(length_allowance_m=.5, max_width_m=1.5, motor_aed=300)
    ops['policy'].update(waste_fraction=.1, margin_fraction=.25, vat_fraction=.1,
                         factory_hours_day=1, holidays=['2026-10-15'])
    ops['checklists']['motorized_roller'] = ['Custom database inspection requirement.']
    result = workflow.run_workflow(project(fabric_id='premium_blackout'))
    assert result['materials']['required_lm'] == 76.56
    assert result['materials']['waste_percent'] == 10
    assert result['costing']['gross_margin_percent'] == 25
    assert result['costing']['vat_percent'] == 10
    assert result['costing']['subtotal'] == round(result['costing']['direct_cost'] / .75, 2)
    assert result['quality']['checklist'] == ['Custom database inspection requirement.']
    assert result['quality']['blockers']
    assert result['production']['manufacture_start'] == '2026-10-16'
    assert result['data_snapshot']['policy']['factory_hours_day'] == 1


def test_new_database_identifiers_need_no_python_enum_edit(database):
    rows, _ = database
    ops = rows['get_operations_snapshot']
    ops['products']['custom_roller'] = {**ops['products']['manual_roller'], 'name': 'Custom database roller'}
    ops['checklists']['custom_roller'] = ['Custom check']
    material = copy.deepcopy(ops['fabrics'][0])
    material.update(id='custom_material', stock_lm=200, compatible=['custom_roller'])
    ops['fabrics'].append(material)
    result = workflow.run_workflow(project(product='custom_roller', fabric_id='custom_material'))
    assert result['requirements']['product_name'] == 'Custom database roller'
    assert result['status'] == 'awaiting_review'


def test_knowledge_uses_edited_database_text_and_new_passage(database):
    rows, _ = database
    corpus = rows['get_company_knowledge_snapshot']
    chunk = next(c for c in corpus['chunks'] if c['id'] == 'RB-SMART-03')
    chunk['content'] = 'The database contains a newly reviewed rechargeable battery description.'
    corpus['chunks'].append({**chunk, 'id': 'RB-SMART-NEW', 'content': 'The database describes a bespoke amber control panel.'})
    answer = knowledge.answer_question('bespoke amber control panel', 'smart')
    assert answer['knowledge_source'] == 'supabase'
    assert answer['citations'][0]['id'] == 'RB-SMART-NEW'
    assert 'amber control panel' in answer['answer']
    assert knowledge.portfolio()['chunk_count'] == 36


def test_database_failure_returns_503_without_fixture_fallback(database, monkeypatch):
    def broken(*args):
        raise RuntimeError('Sensitive raw database failure')

    monkeypatch.setattr(business_data, 'create_client', broken)
    client = TestClient(main.app)
    for endpoint in ('/api/catalog', '/api/health', '/api/knowledge/portfolio'):
        response = client.get(endpoint)
        assert response.status_code == 503
        assert 'No fixture fallback' in response.json()['detail']
        assert 'Sensitive raw' not in response.text
    assert client.post('/api/projects/analyze', json=project().model_dump(mode='json')).status_code == 503


@pytest.mark.parametrize('value', [-1, float('nan')])
def test_invalid_stock_is_rejected_before_agents_run(database, value):
    rows, _ = database
    rows['get_operations_snapshot']['fabrics'][0]['stock_lm'] = value
    with pytest.raises(business_data.BusinessDataUnavailable):
        workflow.run_workflow(project())


def test_unknown_catalog_ids_return_422(database):
    client = TestClient(main.app)
    response = client.post('/api/projects/analyze', json=project(product='missing_product').model_dump(mode='json'))
    assert response.status_code == 422
    assert 'current manufacturing catalog' in response.json()['detail']


def test_catalog_serves_database_scenarios_and_source(database):
    rows, _ = database
    rows['get_operations_snapshot']['scenarios'][0]['title'] = 'Edited database scenario'
    result = TestClient(main.app).get('/api/catalog').json()
    assert result['data_source'] == 'supabase'
    assert result['scenarios'][0]['title'] == 'Edited database scenario'


def test_supabase_sdk_reads_json_snapshot_rpc(database, monkeypatch):
    rows, _ = database
    requests = []

    def handler(request):
        assert request.url.host == 'example.supabase.co'
        assert request.headers['apikey'] == 'fake-server-key'
        assert json.loads(request.content) == {}
        function = request.url.path.rsplit('/', 1)[-1]
        requests.append(function)
        return httpx.Response(200, json=rows[function])

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = real_create_client('https://example.supabase.co', 'fake-server-key',
                                    options=SyncClientOptions(httpx_client=http))
        monkeypatch.setattr(business_data, 'create_client', lambda *args: client)
        assert business_data.load_operations()['data_source'] == 'supabase'
        assert knowledge.answer_question('battery power', 'smart')['knowledge_source'] == 'supabase'
    assert requests == ['get_operations_snapshot', 'get_company_knowledge_snapshot']
