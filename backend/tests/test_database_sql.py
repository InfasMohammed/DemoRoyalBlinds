"""Optional PostgreSQL/pgvector checks, run only against a disposable test DB.

DATABASE_TEST_URL must refer to an empty throwaway database with administrator
rights. These tests create tables and update synthetic rows; never use rbdemo.
"""

import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

if not os.getenv("DATABASE_TEST_URL"):
    pytest.skip(
        "Disposable PostgreSQL not configured; unit tests use mocked Supabase.",
        allow_module_level=True,
    )
psycopg = pytest.importorskip("psycopg")
from app import business_data, knowledge, workflow
from app.models import ProjectRequest

SQL = (Path(__file__).resolve().parents[2] / "supabase/database_setup.sql").read_text()


@pytest.fixture(scope="module")
def pg():
    with psycopg.connect(os.environ["DATABASE_TEST_URL"], autocommit=True) as conn:
        # Standard Supabase roles/schema, created in the disposable DB only.
        conn.execute(
            "create role anon; create role authenticated; create role service_role bypassrls; create schema extensions;"
        )
        conn.execute(
            "grant usage on schema public, extensions to anon, authenticated, service_role;"
        )
        conn.execute(SQL)
        yield conn


def test_full_migration_and_service_role_snapshot_permissions(pg):
    pg.execute("set role service_role")
    try:
        result = pg.execute("select public.get_operations_snapshot()").fetchone()[0]
        assert len(result["fabrics"]) == 3
        assert result["products"]["motorized_roller"]["motor_aed"] == 245
        corpus = pg.execute("select public.get_company_knowledge_snapshot()").fetchone()[0]
        assert len(corpus["products"]) == 15
        assert len(corpus["chunks"]) == 35
        assert "embedding" not in corpus["chunks"][0]
    finally:
        pg.execute("reset role")
    for role in ("anon", "authenticated"):
        pg.execute("set role " + role)
        try:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                pg.execute("select public.get_operations_snapshot()")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                pg.execute("select * from public.inventory_materials")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                pg.execute("select public.get_company_knowledge_snapshot()")
        finally:
            pg.execute("reset role")


def test_added_material_and_knowledge_are_visible_with_service_role_permissions(pg):
    pg.execute("set role service_role")
    try:
        pg.execute(
            """insert into public.inventory_materials
            (id,name,sku,roll_width_m,stock_lm,cost_per_lm,lead_days,transmission,color,compatible,source)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                "mat_added_test",
                "Added demo fabric",
                "ADDED-TEST-SKU",
                2.8,
                17.25,
                35,
                4,
                "Blackout",
                "Ivory",
                ["manual_roller"],
                "Demo supplier quote",
            ),
        )
        pg.execute(
            """insert into public.company_knowledge_chunks
            (id,document_id,title,heading,category,product_ids,content,source_url,source_kind,captured_on)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                "RB-USER-added-test",
                "RB-USER-added-test",
                "Added source",
                "Consultation",
                "company",
                [],
                "The ultramarine showroom protocol covers panel consultations.",
                "https://royalblinds.com/showroom-guide/",
                "user_added_content",
                date(2026, 10, 14),
            ),
        )
        operations = pg.execute("select public.get_operations_snapshot()").fetchone()[0]
        added = next(f for f in operations["fabrics"] if f["id"] == "mat_added_test")
        assert added["stock_lm"] == added["on_hand_lm"] == 17.25
        assert added["reserved_lm"] == 0
        corpus = pg.execute("select public.get_company_knowledge_snapshot()").fetchone()[0]
        passage = next(c for c in corpus["chunks"] if c["id"] == "RB-USER-added-test")
        assert passage["source_kind"] == "user_added_content"
        assert "ultramarine" in passage["content"]
        assert pg.execute(
            "select embedding is null from public.company_knowledge_chunks where id='RB-USER-added-test'"
        ).fetchone()[0]
    finally:
        pg.execute("reset role")
        pg.execute("delete from public.company_knowledge_chunks where id='RB-USER-added-test'")
        pg.execute("delete from public.inventory_materials where id='mat_added_test'")


def test_migration_rerun_preserves_stock_rates_text_and_reports(pg):
    original = pg.execute(
        "select content from public.company_knowledge_chunks where id='RB-SMART-03'"
    ).fetchone()[0]
    pg.execute("update public.inventory_materials set stock_lm=155 where id='linen_blackout'")
    pg.execute("update public.manufacturing_products set motor_aed=299 where id='motorized_roller'")
    pg.execute(
        "update public.company_knowledge_chunks set content='Edited database battery text.' where id='RB-SMART-03'"
    )
    pg.execute(
        "insert into public.demo_reports(id,project_name,status,payload) values ('f1111111-1111-4111-8111-111111111111','Retained test report','blocked','{}')"
    )
    pg.execute(SQL)
    assert (
        pg.execute(
            "select stock_lm from public.inventory_materials where id='linen_blackout'"
        ).fetchone()[0]
        == 155
    )
    assert (
        pg.execute(
            "select motor_aed from public.manufacturing_products where id='motorized_roller'"
        ).fetchone()[0]
        == 299
    )
    assert (
        pg.execute(
            "select content from public.company_knowledge_chunks where id='RB-SMART-03'"
        ).fetchone()[0]
        == "Edited database battery text."
    )
    assert pg.execute("select count(*) from public.demo_reports").fetchone()[0] == 1
    pg.execute("update public.inventory_materials set stock_lm=28 where id='linen_blackout'")
    pg.execute("update public.manufacturing_products set motor_aed=245 where id='motorized_roller'")
    pg.execute(
        "update public.company_knowledge_chunks set content=%s where id='RB-SMART-03'", (original,)
    )


def test_changed_passage_clears_embedding_and_vector_rpc_works(pg):
    vector = "[" + ",".join(["1"] + ["0"] * 1535) + "]"
    pg.execute(
        "update public.company_knowledge_chunks set embedding=%s::extensions.vector, embedding_model='text-embedding-3-small' where id='RB-SMART-03'",
        (vector,),
    )
    result = pg.execute(
        "select * from public.match_company_knowledge(%s::extensions.vector, %s, null, 1)",
        (vector, "smart"),
    ).fetchone()
    assert result[0] == "RB-SMART-03"
    original = pg.execute(
        "select content from public.company_knowledge_chunks where id='RB-SMART-03'"
    ).fetchone()[0]
    pg.execute(
        "update public.company_knowledge_chunks set content=content || ' Updated.' where id='RB-SMART-03'"
    )
    assert pg.execute(
        "select embedding,embedding_model from public.company_knowledge_chunks where id='RB-SMART-03'"
    ).fetchone() == (None, None)
    pg.execute(
        "update public.company_knowledge_chunks set content=%s where id='RB-SMART-03'", (original,)
    )


def test_agents_and_knowledge_read_current_postgres_records(pg, monkeypatch):
    calls = []

    class Client:
        def rpc(self, name, arguments):
            assert name in ("get_operations_snapshot", "get_company_knowledge_snapshot")
            calls.append(name)
            return SimpleNamespace(
                execute=lambda: SimpleNamespace(
                    data=pg.execute("select public." + name + "()").fetchone()[0]
                )
            )

    monkeypatch.setenv("BUSINESS_DATA_SOURCE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake-test-key")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("KNOWLEDGE_RETRIEVAL_MODE", "local")
    monkeypatch.setattr(business_data, "create_client", lambda *args: Client())
    request = ProjectRequest(
        customer="Test customer",
        project_name="SQL backed agents",
        brief="24 motorized rollers.",
        due_date=date(2099, 1, 1),
    )
    before = workflow.run_workflow(request)
    assert before["status"] == "blocked"
    pg.execute("update public.inventory_materials set stock_lm=200 where id='linen_blackout'")
    pg.execute(
        "update public.manufacturing_settings set policy=jsonb_set(policy,'{margin_fraction}','0.25') where id='default'"
    )
    after = workflow.run_workflow(request)
    assert after["status"] == "awaiting_review"
    assert after["costing"]["gross_margin_percent"] == 25
    assert after["costing"]["subtotal"] == round(after["costing"]["direct_cost"] / 0.75, 2)
    assert all(row["data_source"] == "supabase" for row in after["traces"])
    assert len(calls) == 4
    pg.execute(
        "update public.company_knowledge_chunks set content='The database mentions a reviewed amber controller.' where id='RB-SMART-03'"
    )
    answer = knowledge.answer_question("amber controller", "smart")
    assert answer["citations"][0]["id"] == "RB-SMART-03"
    assert answer["knowledge_source"] == "supabase"
    assert "amber controller" in answer["answer"]


@pytest.fixture
def execution_db(pg, monkeypatch):
    import json

    from psycopg.types.json import Jsonb

    from app.store import ReportStore

    # Only this disposable test DB is reset. Never run this suite on rbdemo.
    pg.execute(
        "delete from public.project_events; delete from public.work_order_tasks; delete from public.production_bookings; delete from public.material_reservations; delete from public.work_orders; delete from public.approval_jobs; delete from public.demo_reports;"
    )
    seed = json.loads(
        (Path(__file__).resolve().parents[1] / "app/data/demo_operations.json").read_text()
    )
    pg.execute(
        "update public.manufacturing_settings set policy=%s,is_sample=true where id='default'",
        (Jsonb(seed["policy"]),),
    )
    for fabric in seed["fabrics"]:
        pg.execute(
            "update public.inventory_materials set stock_lm=%s where id=%s",
            (fabric["stock_lm"], fabric["id"]),
        )
    pg.execute("update public.manufacturing_products set motor_aed=245 where id='motorized_roller'")
    monkeypatch.setenv("BUSINESS_DATA_SOURCE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake-test-key")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("KNOWLEDGE_RETRIEVAL_MODE", "local")

    class Client:
        def rpc(self, name, args):
            def execute():
                parameters = []
                values = []
                for key, value in args.items():
                    cast = (
                        "uuid[]"
                        if key == "p_checked_ids"
                        else "jsonb"
                        if key in ("p_approval", "p_plan", "p_findings")
                        else "uuid"
                        if key == "p_report_id"
                        else "text"
                    )
                    parameters.append(key + " => %s::" + cast)
                    values.append(Jsonb(value) if cast == "jsonb" else value)
                try:
                    payload = pg.execute(
                        "select public." + name + "(" + ",".join(parameters) + ")", values
                    ).fetchone()[0]
                except psycopg.errors.RaiseException as exc:
                    from postgrest.exceptions import APIError

                    raise APIError(
                        {
                            "code": "P0001",
                            "message": exc.diag.message_primary,
                            "details": None,
                            "hint": None,
                        }
                    ) from exc
                return SimpleNamespace(data=payload)

            return SimpleNamespace(execute=execute)

    monkeypatch.setattr(business_data, "create_client", lambda *args: Client())
    store = ReportStore()
    store.client = Client()
    # Reads/saves below use SQL directly; action methods use the real RPC paths.
    monkeypatch.setattr(
        store,
        "get",
        lambda id: (
            pg.execute("select payload from public.demo_reports where id=%s", (id,)).fetchone()
            or [None]
        )[0],
    )
    monkeypatch.setattr(
        store,
        "save",
        lambda report: pg.execute(
            "insert into public.demo_reports(id,project_name,status,payload) values(%s,%s,%s,%s)",
            (report["id"], report["request"]["project_name"], report["status"], Jsonb(report)),
        ),
    )
    return store, Client, seed


def sql_report(store, quantity=24, due_date=date(2099, 1, 1)):
    report = workflow.run_workflow(
        ProjectRequest(
            customer="Demo customer",
            project_name="Execution SQL test",
            brief="Manufacture motorized roller blinds.",
            fabric_id="premium_blackout",
            quantity=quantity,
            due_date=due_date,
        )
    )
    assert report["status"] == "awaiting_review"
    store.save(report)
    return report


def sql_approval():
    return {
        "reviewer": "SQL reviewer",
        "measurements_confirmed": True,
        "specification_confirmed": True,
        "commercial_terms_confirmed": True,
        "execution_confirmed": True,
        "approved_at": "2026-10-13T12:00:00Z",
    }


def test_sql_approval_authorization_and_queue_are_atomic(pg, execution_db):
    from psycopg.types.json import Jsonb

    store, _, _ = execution_db
    report = sql_report(store)
    with pytest.raises(psycopg.errors.RaiseException):
        pg.execute(
            "select public.approve_project(%s,%s)",
            (report["id"], Jsonb({**sql_approval(), "execution_confirmed": False})),
        )
    assert store.get(report["id"])["status"] == "awaiting_review"
    assert pg.execute("select count(*) from public.approval_jobs").fetchone()[0] == 0
    result = store.approve(report["id"], sql_approval())
    assert result["execution"]["status"] == "queued"
    assert store.approve(report["id"], sql_approval())["approval"] == result["approval"]
    assert pg.execute("select count(*) from public.project_events").fetchone()[0] == 1


def test_sql_workflow_consumption_quality_and_retries(pg, execution_db):
    from app.execution import run_post_approval

    store, _, _ = execution_db
    report = sql_report(store)
    store.approve(report["id"], sql_approval())
    result = run_post_approval(store, report["id"])
    assert result["execution"]["status"] == "completed"
    assert result["execution"]["reservation"]["quantity_lm"] == 68.69
    assert (
        pg.execute(
            "select stock_lm from public.inventory_materials where id='premium_blackout'"
        ).fetchone()[0]
        == 120
    )
    assert len(result["execution"]["tasks"]) == 9
    assert (
        run_post_approval(store, report["id"])["execution"]["work_order"]["id"]
        == result["execution"]["work_order"]["id"]
    )
    store.advance(report["id"], "start_production", "Operator")
    store.advance(report["id"], "finish_production", "Operator")
    remaining = pg.execute(
        "select stock_lm from public.inventory_materials where id='premium_blackout'"
    ).fetchone()[0]
    assert float(remaining) == 51.31
    store.advance(report["id"], "finish_production", "Operator")
    assert (
        pg.execute(
            "select stock_lm from public.inventory_materials where id='premium_blackout'"
        ).fetchone()[0]
        == remaining
    )
    with pytest.raises(Exception, match="Every quality check"):
        store.advance(report["id"], "pass_quality", "Inspector")
    failed = store.advance(report["id"], "fail_quality", "Inspector", "Alignment needs correction.")
    assert all(
        t["status"] == "failed" for t in failed["execution"]["tasks"] if t["stage"] == "quality"
    )
    checks = [t["id"] for t in result["execution"]["tasks"] if t["stage"] == "quality"]
    store.advance(report["id"], "pass_quality", "Inspector", "All checks repeated.", checks)
    complete = store.advance(report["id"], "complete_installation", "Installer")
    assert complete["execution"]["work_order"]["status"] == "completed"
    assert all(t["status"] == "completed" for t in complete["execution"]["tasks"])


def test_sql_cancel_releases_unused_stock_and_preserves_consumption(pg, execution_db):
    from app.execution import run_post_approval

    store, _, _ = execution_db
    report = sql_report(store, 4)
    store.approve(report["id"], sql_approval())
    run_post_approval(store, report["id"])
    cancelled = store.advance(report["id"], "cancel", "Operator", "Cancelled before production.")
    assert cancelled["execution"]["reservation"]["status"] == "released"
    assert all(b["released"] for b in cancelled["execution"]["bookings"])
    assert (
        pg.execute(
            "select stock_lm from public.inventory_materials where id='premium_blackout'"
        ).fetchone()[0]
        == 120
    )
    another = sql_report(store, 4)
    store.approve(another["id"], sql_approval())
    run_post_approval(store, another["id"])
    store.advance(another["id"], "start_production", "Operator")
    store.advance(another["id"], "finish_production", "Operator")
    consumed = store.advance(
        another["id"], "cancel", "Operator", "Installation cancelled after manufacturing."
    )
    assert consumed["execution"]["reservation"]["status"] == "consumed"
    assert all(
        not b["released"] for b in consumed["execution"]["bookings"] if b["stage"] == "factory"
    )


def test_sql_capacity_deadline_failure_rolls_back_reservation_and_work_order(pg, execution_db):
    from app.execution import run_post_approval

    store, _, _ = execution_db
    temp = workflow.run_workflow(
        ProjectRequest(
            customer="Demo customer",
            project_name="Date probe",
            brief="Ten motorized blinds.",
            fabric_id="premium_blackout",
            quantity=10,
            due_date=date(2099, 1, 1),
        )
    )
    deadline = date.fromisoformat(temp["production"]["completion_date"])
    reports = [sql_report(store, 10, deadline), sql_report(store, 10, deadline)]
    for report in reports:
        store.approve(report["id"], sql_approval())
    first = run_post_approval(store, reports[0]["id"])
    second = run_post_approval(store, reports[1]["id"])
    assert first["execution"]["status"] == "completed"
    assert second["execution"]["status"] == "blocked"
    assert "insufficient capacity" in second["execution"]["reason"]
    assert second["execution"]["work_order"] is None and second["execution"]["reservation"] is None
    assert pg.execute("select count(*) from public.work_orders").fetchone()[0] == 1
    assert pg.execute("select count(*) from public.material_reservations").fetchone()[0] == 1
    assert (
        pg.execute(
            "select max(hours) from (select sum(hours) hours from public.production_bookings where not released group by stage,work_date) daily"
        ).fetchone()[0]
        <= 6
    )


def test_sql_changed_prices_block_actions_before_stock_mutation(pg, execution_db):
    from app.execution import run_post_approval

    store, _, _ = execution_db
    report = sql_report(store)
    store.approve(report["id"], sql_approval())
    pg.execute("update public.manufacturing_products set motor_aed=999 where id='motorized_roller'")
    result = run_post_approval(store, report["id"])
    assert result["execution"]["status"] == "blocked"
    assert "rates or planning settings changed" in result["execution"]["reason"]
    assert pg.execute("select count(*) from public.material_reservations").fetchone()[0] == 0


def test_sql_concurrent_reservations_cannot_oversell(pg, execution_db):
    from concurrent.futures import ThreadPoolExecutor

    from psycopg.types.json import Jsonb

    from app.workflow import calculate_production

    store, _, _ = execution_db
    reports = [sql_report(store), sql_report(store)]
    for report in reports:
        store.approve(report["id"], sql_approval())

    def activate(report):
        snapshot = report["data_snapshot"]
        plan = calculate_production(
            report["request"],
            snapshot["products"][report["request"]["product"]],
            snapshot["policy"],
        )
        with psycopg.connect(os.environ["DATABASE_TEST_URL"], autocommit=True) as conn:
            return conn.execute(
                "select public.execute_approved_project(%s,%s,%s)",
                (report["id"], Jsonb(plan), Jsonb([])),
            ).fetchone()[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(activate, reports))
    assert sorted(r["execution"]["status"] for r in results) == ["blocked", "completed"]
    assert float(
        pg.execute(
            "select sum(quantity_lm) from public.material_reservations where status='active'"
        ).fetchone()[0]
    ) == pytest.approx(68.69)


def test_sql_progress_rpc_is_not_available_to_browser_roles(pg, execution_db):
    store, _, _ = execution_db
    report = sql_report(store)
    for role in ("anon", "authenticated"):
        pg.execute("set role " + role)
        try:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                pg.execute("select public.approve_project(%s,'{}'::jsonb)", (report["id"],))
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                pg.execute("select * from public.material_reservations")
        finally:
            pg.execute("reset role")
