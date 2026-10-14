"""Build repeatable, non-destructive database migrations from labeled seed data."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from export_knowledge_sql import export_sql, literal

from app.knowledge import DATA


def operations_sql():
    seed = json.loads((ROOT / "backend/app/data/demo_operations.json").read_text())
    sql = """-- Operational business records. Initial values are synthetic interview seeds.
-- Reruns preserve edited stock, rates, limits, settings and existing reports.
begin;
create table if not exists public.manufacturing_products (
  id text primary key,
  name text not null,
  estimation_kind text not null check (estimation_kind in ('roller', 'curtain')),
  knowledge_product_id text not null references public.company_products(id),
  hardware_aed numeric not null check (hardware_aed >= 0),
  motor_aed numeric not null check (motor_aed >= 0),
  labor_hours numeric not null check (labor_hours > 0),
  install_hours numeric not null check (install_hours > 0),
  max_width_m numeric not null check (max_width_m > 0),
  max_height_m numeric not null check (max_height_m > 0),
  width_allowance_m numeric not null check (width_allowance_m >= 0),
  length_allowance_m numeric not null check (length_allowance_m >= 0),
  fullness numeric not null check (fullness > 0),
  quality_checklist text[] not null check (cardinality(quality_checklist) > 0),
  source text not null,
  updated_at timestamptz not null default now()
);
create table if not exists public.inventory_materials (
  id text primary key,
  name text not null,
  sku text not null unique,
  roll_width_m numeric not null check (roll_width_m > 0),
  stock_lm numeric not null check (stock_lm >= 0),
  cost_per_lm numeric not null check (cost_per_lm >= 0),
  lead_days integer not null check (lead_days >= 0),
  transmission text not null,
  color text not null,
  compatible text[] not null check (cardinality(compatible) > 0),
  source text not null,
  updated_at timestamptz not null default now()
);
create table if not exists public.manufacturing_settings (
  id text primary key check (id = 'default'),
  policy jsonb not null,
  scenarios jsonb not null,
  provenance text not null,
  is_sample boolean not null default true,
  updated_at timestamptz not null default now()
);
create table if not exists public.company_knowledge_settings (
  id text primary key check (id = 'default'),
  metadata jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.manufacturing_products enable row level security;
alter table public.inventory_materials enable row level security;
alter table public.manufacturing_settings enable row level security;
alter table public.company_knowledge_settings enable row level security;
revoke all on public.manufacturing_products, public.inventory_materials,
  public.manufacturing_settings, public.company_knowledge_settings from anon, authenticated;
grant select, insert, update on public.manufacturing_products, public.inventory_materials,
  public.manufacturing_settings, public.company_knowledge_settings to service_role;
comment on table public.inventory_materials is 'Editable stock records; seeded sample values are not verified Royal Blinds inventory. Analysis reads without reserving stock.';

create or replace function public.touch_business_record()
returns trigger language plpgsql set search_path = public, pg_temp
as $trigger$
begin
  new.updated_at := now();
  return new;
end;
$trigger$;
"""
    for table in (
        "manufacturing_products",
        "inventory_materials",
        "manufacturing_settings",
        "company_knowledge_settings",
    ):
        sql += f"drop trigger if exists business_record_updated on public.{table};\n"
        sql += f"create trigger business_record_updated before update on public.{table} for each row execute function public.touch_business_record();\n"
    for id, p in seed["products"].items():
        fields = ["id", *p.keys(), "quality_checklist"]
        values = [
            literal(id),
            *(literal(v) if isinstance(v, str) else str(v) for v in p.values()),
            "array[" + ",".join(literal(v) for v in seed["checklists"][id]) + "]::text[]",
        ]
        sql += f"insert into public.manufacturing_products ({', '.join(fields)}) values ({', '.join(values)}) on conflict (id) do nothing;\n"
    for f in seed["fabrics"]:
        values = [
            literal(v)
            if isinstance(v, str)
            else "array[" + ",".join(literal(x) for x in v) + "]::text[]"
            if isinstance(v, list)
            else str(v)
            for v in f.values()
        ]
        sql += f"insert into public.inventory_materials ({', '.join(f)}) values ({', '.join(values)}) on conflict (id) do nothing;\n"
    sql += "insert into public.manufacturing_settings (id, policy, scenarios, provenance, is_sample) values ('default', "
    sql += ", ".join(
        [
            literal(json.dumps(seed["policy"])) + "::jsonb",
            literal(json.dumps(seed["scenarios"])) + "::jsonb",
            literal(seed["provenance"]),
            "true",
        ]
    )
    sql += ") on conflict (id) do nothing;\n"
    metadata = {key: value for key, value in DATA.items() if key not in ("products", "documents")}
    sql += (
        "insert into public.company_knowledge_settings (id, metadata) values ('default', "
        + literal(json.dumps(metadata))
        + "::jsonb) on conflict (id) do nothing;\n"
    )
    sql += """
-- Each RPC uses one SQL statement, so readers get one consistent MVCC snapshot.
create or replace function public.get_operations_snapshot()
returns jsonb language sql stable security invoker set search_path = public, pg_temp
as $function$
 select jsonb_build_object(
   'products', (select jsonb_object_agg(p.id, to_jsonb(p) - 'id' - 'quality_checklist') from public.manufacturing_products p),
   'fabrics', (select jsonb_agg(to_jsonb(m) order by m.id) from public.inventory_materials m),
   'checklists', (select jsonb_object_agg(p.id, to_jsonb(p.quality_checklist)) from public.manufacturing_products p),
   'policy', s.policy, 'scenarios', s.scenarios, 'provenance', s.provenance, 'is_sample', s.is_sample)
 from public.manufacturing_settings s where s.id = 'default';
$function$;
create or replace function public.get_company_knowledge_snapshot()
returns jsonb language sql stable security invoker set search_path = public, pg_temp
as $function$
 select jsonb_build_object(
   'products', (select jsonb_agg(to_jsonb(p) order by p.id) from public.company_products p),
   'chunks', (select jsonb_agg(to_jsonb(c) - 'embedding' - 'embedding_model' order by c.id) from public.company_knowledge_chunks c),
   'metadata', s.metadata)
 from public.company_knowledge_settings s where s.id = 'default';
$function$;
revoke all on function public.get_operations_snapshot() from public, anon, authenticated;
revoke all on function public.get_company_knowledge_snapshot() from public, anon, authenticated;
grant execute on function public.get_operations_snapshot() to service_role;
grant execute on function public.get_company_knowledge_snapshot() to service_role;
commit;
"""
    execution = (
        (ROOT / "supabase/post_approval.sql")
        .read_text()
        .replace("begin;", "", 1)
        .rsplit("commit;", 1)[0]
    )
    return sql.rsplit("commit;", 1)[0] + "\n" + execution + "\ncommit;\n"


def combined_sql():
    # Combine into one transaction. A failure rolls back the whole migration.
    knowledge = export_sql().split("commit;")[0].replace("begin;", "", 1)
    operations = operations_sql().replace("begin;", "", 1).rsplit("commit;", 1)[0]
    return (
        "-- Full additive setup. Preserve existing reports and edited business records.\nbegin;\n"
        + (ROOT / "supabase/schema.sql").read_text()
        + "\n"
        + knowledge
        + "\n"
        + operations
        + "\ncommit;\n"
    )


if __name__ == "__main__":
    (ROOT / "supabase/knowledge_base.sql").write_text(export_sql())
    (ROOT / "supabase/operations.sql").write_text(operations_sql())
    (ROOT / "supabase/database_setup.sql").write_text(combined_sql())
    print(
        "Exported knowledge_base.sql, operations.sql and the complete database_setup.sql. Reruns preserve database edits."
    )
