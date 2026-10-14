import copy
import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions

from app import business_data, knowledge, main, record_creation


def material(**changes):
    return dict(request_id=str(uuid4()), name='New demo fabric', sku='NEW-SKU', roll_width_m=2.8,
                stock_lm=25.5, cost_per_lm=35, lead_days=4, transmission='Blackout', color='Ivory',
                compatible=['manual_roller'], source='Demo supplier quotation', **changes)


def passage(**changes):
    data = dict(request_id=str(uuid4()), title='New showroom guidance', heading='Panel consultation',
                category='company', product_ids=[], content='The ultramarine showroom panel protocol is used during sample consultations.',
                source_url='https://royalblinds.com/showroom-guide/', reviewed=True)
    return {**data, **changes}


@pytest.fixture
def database(monkeypatch):
    ops = copy.deepcopy(business_data.load_operations())
    corpus = copy.deepcopy(knowledge.load_corpus())
    metadata = {k: v for k, v in corpus.items() if k not in ('products', 'chunks', 'documents', 'data_source')}
    tables = {'inventory_materials': {f['id']: f for f in ops['fabrics']},
              'company_knowledge_chunks': {c['id']: c for c in corpus['chunks']}}
    state = {'fail_writes': False, 'writes': 0}

    def handler(request):
        assert request.url.host == 'example.supabase.co'
        assert request.headers['apikey'] == 'fake-server-key'
        name = request.url.path.rsplit('/', 1)[-1]
        if name == 'get_operations_snapshot':
            return httpx.Response(200, json={**ops, 'fabrics': list(tables['inventory_materials'].values())})
        if name == 'get_company_knowledge_snapshot':
            return httpx.Response(200, json={'metadata': metadata, 'products': corpus['products'],
                                           'chunks': list(tables['company_knowledge_chunks'].values())})
        rows = tables[name]
        if request.method == 'POST':
            row = json.loads(request.content)
            if state['fail_writes']:
                return httpx.Response(500, json={'code': 'XX000', 'message': 'Sensitive database details', 'details': None, 'hint': None})
            duplicate = row['id'] in rows or name == 'inventory_materials' and any(r['sku'] == row['sku'] for r in rows.values())
            if duplicate:
                return httpx.Response(409, json={'code': '23505', 'message': 'Sensitive uniqueness details', 'details': None, 'hint': None})
            state['writes'] += 1
            rows[row['id']] = row
            return httpx.Response(201, json=[row])
        assert request.method == 'GET'
        id = request.url.params['id'].removeprefix('eq.')
        return httpx.Response(200, json=[rows[id]] if id in rows else [])

    monkeypatch.setenv('BUSINESS_DATA_SOURCE', 'supabase')
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'fake-server-key')
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    monkeypatch.setenv('KNOWLEDGE_RETRIEVAL_MODE', 'local')
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = create_client('https://example.supabase.co', 'fake-server-key', options=SyncClientOptions(httpx_client=http))
        monkeypatch.setattr(business_data, 'create_client', lambda *args: client)
        monkeypatch.setattr(record_creation, 'create_client', lambda *args: client)
        yield TestClient(main.app), tables, state


def test_material_save_is_visible_to_catalog_and_inventory_agent(database):
    client, tables, _ = database
    existing = copy.deepcopy(tables['inventory_materials'])
    response = client.post('/api/materials', json=material())
    assert response.status_code == 201
    id = response.json()['record']['id']
    saved = next(f for f in client.get('/api/catalog').json()['fabrics'] if f['id'] == id)
    assert saved['stock_lm'] == saved['on_hand_lm'] == 25.5
    assert saved['reserved_lm'] == 0
    analyzed = client.post('/api/projects/analyze', json={
        'customer': 'Demo customer', 'project_name': 'New material quotation', 'brief': 'Manual rollers for a demo office.',
        'product': 'manual_roller', 'fabric_id': id, 'quantity': 2, 'width_m': .8, 'height_m': 1,
        'due_date': '2099-01-01', 'site': 'Dubai demo site',
    })
    assert analyzed.status_code == 201
    assert analyzed.json()['materials']['fabric']['id'] == id
    assert all(tables['inventory_materials'][key] == value for key, value in existing.items())


def test_knowledge_save_is_immediately_retrievable_with_source_metadata(database):
    client, tables, _ = database
    response = client.post('/api/knowledge/entries', json=passage())
    assert response.status_code == 201
    record = response.json()['record']
    assert record['source_kind'] == 'user_added_content'
    assert 'reviewed' not in record
    assert 'embedding' not in record
    assert response.json()['indexing_status'] == 'pending'
    assert client.get('/api/knowledge/portfolio').json()['chunk_count'] == 36
    answer = client.post('/api/knowledge/ask', json={'question': 'ultramarine showroom panel protocol'}).json()
    assert answer['knowledge_source'] == 'supabase'
    assert answer['citations'][0]['id'] == record['id']
    assert answer['citations'][0]['source_url'] == record['source_url']
    assert record['id'] in tables['company_knowledge_chunks']


@pytest.mark.parametrize(('endpoint', 'payload'), [('/api/materials', material()), ('/api/knowledge/entries', passage())])
def test_same_form_retry_does_not_duplicate_records(database, endpoint, payload):
    client, _, state = database
    first = client.post(endpoint, json=payload)
    retry = client.post(endpoint, json=payload)
    assert first.status_code == retry.status_code == 201
    assert first.json()['created'] is True
    assert retry.json()['created'] is False
    assert first.json()['record']['id'] == retry.json()['record']['id']
    assert state['writes'] == 1


def test_duplicate_sku_and_changed_retry_never_overwrite(database):
    client, tables, state = database
    original = material()
    id = client.post('/api/materials', json=original).json()['record']['id']
    for payload in ({**original, 'request_id': str(uuid4())}, {**original, 'stock_lm': 900}):
        response = client.post('/api/materials', json=payload)
        assert response.status_code == 409
        assert 'Sensitive uniqueness' not in response.text
    assert tables['inventory_materials'][id]['stock_lm'] == 25.5
    assert state['writes'] == 1


@pytest.mark.parametrize(('endpoint', 'payload'), [
    ('/api/materials', {**material(), 'stock_lm': -1}),
    ('/api/materials', {**material(), 'compatible': ['unknown']}),
    ('/api/knowledge/entries', passage(reviewed=False)),
    ('/api/knowledge/entries', passage(source_url='javascript:alert(1)')),
    ('/api/knowledge/entries', passage(product_ids=['unknown'])),
    ('/api/knowledge/entries', passage(category='external', product_ids=['curtains'])),
])
def test_invalid_records_cannot_write(database, endpoint, payload):
    client, _, state = database
    assert client.post(endpoint, json=payload).status_code == 422
    assert state['writes'] == 0


def test_database_write_failure_is_safe_and_never_claims_success(database):
    client, _, state = database
    state['fail_writes'] = True
    response = client.post('/api/materials', json=material())
    assert response.status_code == 503
    assert 'Sensitive database' not in response.text
    assert state['writes'] == 0


def test_offline_mode_does_not_save_to_database_or_fixtures(monkeypatch):
    monkeypatch.setenv('BUSINESS_DATA_SOURCE', 'demo')
    client = TestClient(main.app)
    for endpoint, payload in (('/api/materials', material()), ('/api/knowledge/entries', passage())):
        response = client.post(endpoint, json=payload)
        assert response.status_code == 503
        assert 'offline fixtures are not changed' in response.json()['detail']
