"""Optional PostgreSQL/pgvector checks, run only against a disposable test DB.

DATABASE_TEST_URL must refer to an empty throwaway database with administrator
rights. These tests create tables and update synthetic rows; never use rbdemo.
"""
import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

if not os.getenv('DATABASE_TEST_URL'):
    pytest.skip('Disposable PostgreSQL not configured; unit tests use mocked Supabase.', allow_module_level=True)
psycopg = pytest.importorskip('psycopg')
from app import business_data, knowledge, workflow
from app.models import ProjectRequest

SQL = (Path(__file__).resolve().parents[2] / 'supabase/database_setup.sql').read_text()


@pytest.fixture(scope='module')
def pg():
    with psycopg.connect(os.environ['DATABASE_TEST_URL'], autocommit=True) as conn:
        # Standard Supabase roles/schema, created in the disposable DB only.
        conn.execute('create role anon; create role authenticated; create role service_role bypassrls; create schema extensions;')
        conn.execute('grant usage on schema public, extensions to anon, authenticated, service_role;')
        conn.execute(SQL)
        yield conn


def test_full_migration_and_service_role_snapshot_permissions(pg):
    pg.execute('set role service_role')
    try:
        result = pg.execute('select public.get_operations_snapshot()').fetchone()[0]
        assert len(result['fabrics']) == 3
        assert result['products']['motorized_roller']['motor_aed'] == 245
        corpus = pg.execute('select public.get_company_knowledge_snapshot()').fetchone()[0]
        assert len(corpus['products']) == 15
        assert len(corpus['chunks']) == 35
        assert 'embedding' not in corpus['chunks'][0]
    finally:
        pg.execute('reset role')
    for role in ('anon', 'authenticated'):
        pg.execute('set role ' + role)
        try:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                pg.execute('select public.get_operations_snapshot()')
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                pg.execute('select * from public.inventory_materials')
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                pg.execute('select public.get_company_knowledge_snapshot()')
        finally:
            pg.execute('reset role')


def test_migration_rerun_preserves_stock_rates_text_and_reports(pg):
    original = pg.execute("select content from public.company_knowledge_chunks where id='RB-SMART-03'").fetchone()[0]
    pg.execute("update public.inventory_materials set stock_lm=155 where id='linen_blackout'")
    pg.execute("update public.manufacturing_products set motor_aed=299 where id='motorized_roller'")
    pg.execute("update public.company_knowledge_chunks set content='Edited database battery text.' where id='RB-SMART-03'")
    pg.execute("insert into public.demo_reports(id,project_name,status,payload) values ('f1111111-1111-4111-8111-111111111111','Retained test report','blocked','{}')")
    pg.execute(SQL)
    assert pg.execute("select stock_lm from public.inventory_materials where id='linen_blackout'").fetchone()[0] == 155
    assert pg.execute("select motor_aed from public.manufacturing_products where id='motorized_roller'").fetchone()[0] == 299
    assert pg.execute("select content from public.company_knowledge_chunks where id='RB-SMART-03'").fetchone()[0] == 'Edited database battery text.'
    assert pg.execute('select count(*) from public.demo_reports').fetchone()[0] == 1
    pg.execute("update public.inventory_materials set stock_lm=28 where id='linen_blackout'")
    pg.execute("update public.manufacturing_products set motor_aed=245 where id='motorized_roller'")
    pg.execute("update public.company_knowledge_chunks set content=%s where id='RB-SMART-03'", (original,))


def test_changed_passage_clears_embedding_and_vector_rpc_works(pg):
    vector = '[' + ','.join(['1'] + ['0'] * 1535) + ']'
    pg.execute("update public.company_knowledge_chunks set embedding=%s::extensions.vector, embedding_model='text-embedding-3-small' where id='RB-SMART-03'", (vector,))
    result = pg.execute('select * from public.match_company_knowledge(%s::extensions.vector, %s, null, 1)', (vector, 'smart')).fetchone()
    assert result[0] == 'RB-SMART-03'
    original = pg.execute("select content from public.company_knowledge_chunks where id='RB-SMART-03'").fetchone()[0]
    pg.execute("update public.company_knowledge_chunks set content=content || ' Updated.' where id='RB-SMART-03'")
    assert pg.execute("select embedding,embedding_model from public.company_knowledge_chunks where id='RB-SMART-03'").fetchone() == (None, None)
    pg.execute("update public.company_knowledge_chunks set content=%s where id='RB-SMART-03'", (original,))


def test_agents_and_knowledge_read_current_postgres_records(pg, monkeypatch):
    calls = []

    class Client:
        def rpc(self, name, arguments):
            assert name in ('get_operations_snapshot', 'get_company_knowledge_snapshot')
            calls.append(name)
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=pg.execute('select public.' + name + '()').fetchone()[0]))

    monkeypatch.setenv('BUSINESS_DATA_SOURCE', 'supabase')
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'fake-test-key')
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    monkeypatch.setenv('KNOWLEDGE_RETRIEVAL_MODE', 'local')
    monkeypatch.setattr(business_data, 'create_client', lambda *args: Client())
    request = ProjectRequest(customer='Test customer', project_name='SQL backed agents',
                             brief='24 motorized rollers.', due_date=date(2099, 1, 1))
    before = workflow.run_workflow(request)
    assert before['status'] == 'blocked'
    pg.execute("update public.inventory_materials set stock_lm=200 where id='linen_blackout'")
    pg.execute("update public.manufacturing_settings set policy=jsonb_set(policy,'{margin_fraction}','0.25') where id='default'")
    after = workflow.run_workflow(request)
    assert after['status'] == 'awaiting_review'
    assert after['costing']['gross_margin_percent'] == 25
    assert after['costing']['subtotal'] == round(after['costing']['direct_cost'] / .75, 2)
    assert all(row['data_source'] == 'supabase' for row in after['traces'])
    assert len(calls) == 4
    pg.execute("update public.company_knowledge_chunks set content='The database mentions a reviewed amber controller.' where id='RB-SMART-03'")
    answer = knowledge.answer_question('amber controller', 'smart')
    assert answer['citations'][0]['id'] == 'RB-SMART-03'
    assert answer['knowledge_source'] == 'supabase'
    assert 'amber controller' in answer['answer']
