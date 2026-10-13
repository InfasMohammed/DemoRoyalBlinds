-- Operational business records. Initial values are synthetic interview seeds.
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
drop trigger if exists business_record_updated on public.manufacturing_products;
create trigger business_record_updated before update on public.manufacturing_products for each row execute function public.touch_business_record();
drop trigger if exists business_record_updated on public.inventory_materials;
create trigger business_record_updated before update on public.inventory_materials for each row execute function public.touch_business_record();
drop trigger if exists business_record_updated on public.manufacturing_settings;
create trigger business_record_updated before update on public.manufacturing_settings for each row execute function public.touch_business_record();
drop trigger if exists business_record_updated on public.company_knowledge_settings;
create trigger business_record_updated before update on public.company_knowledge_settings for each row execute function public.touch_business_record();
insert into public.manufacturing_products (id, name, hardware_aed, motor_aed, labor_hours, install_hours, max_width_m, max_height_m, estimation_kind, knowledge_product_id, width_allowance_m, length_allowance_m, fullness, source, quality_checklist) values ('motorized_roller', 'Motorized roller blinds', 85, 245, 0.55, 0.4, 3.0, 3.5, 'roller', 'roller_blinds', 0.1, 0.25, 1, 'Sample product specification · motorized_roller', array['Confirm each opening by site survey; record tolerances.','Approve a physical fabric sample and light-control specification.','Inspect fabric for defects before cutting and record batch traceability.','Check finished dimensions, alignment and smooth operation.','Check fixing substrate, access conditions and installer safety plan.','Qualified installer to verify power, motor load and wiring.','Test limit settings, remote pairing and safe operation.']::text[]) on conflict (id) do nothing;
insert into public.manufacturing_products (id, name, hardware_aed, motor_aed, labor_hours, install_hours, max_width_m, max_height_m, estimation_kind, knowledge_product_id, width_allowance_m, length_allowance_m, fullness, source, quality_checklist) values ('manual_roller', 'Manual roller blinds', 65, 0, 0.4, 0.3, 3.0, 3.5, 'roller', 'roller_blinds', 0.1, 0.25, 1, 'Sample product specification · manual_roller', array['Confirm each opening by site survey; record tolerances.','Approve a physical fabric sample and light-control specification.','Inspect fabric for defects before cutting and record batch traceability.','Check finished dimensions, alignment and smooth operation.','Check fixing substrate, access conditions and installer safety plan.','Confirm applicable cord/chain safety requirements and fit approved restraints.']::text[]) on conflict (id) do nothing;
insert into public.manufacturing_products (id, name, hardware_aed, motor_aed, labor_hours, install_hours, max_width_m, max_height_m, estimation_kind, knowledge_product_id, width_allowance_m, length_allowance_m, fullness, source, quality_checklist) values ('curtain', 'Curtains with manual tracks', 95, 0, 0.85, 0.5, 4.0, 4.0, 'curtain', 'curtains', 0, 0.3, 2, 'Sample product specification · curtain', array['Confirm each opening by site survey; record tolerances.','Approve a physical fabric sample and light-control specification.','Inspect fabric for defects before cutting and record batch traceability.','Check finished dimensions, alignment and smooth operation.','Check fixing substrate, access conditions and installer safety plan.']::text[]) on conflict (id) do nothing;
insert into public.inventory_materials (id, name, sku, roll_width_m, stock_lm, cost_per_lm, lead_days, transmission, color, compatible, source) values ('linen_blackout', 'Linen-look blackout', 'DEMO-FAB-101', 3.2, 28.0, 52.0, 7, 'Blackout', 'Warm ivory', array['motorized_roller','manual_roller','curtain']::text[], 'Demo warehouse · WH-001') on conflict (id) do nothing;
insert into public.inventory_materials (id, name, sku, roll_width_m, stock_lm, cost_per_lm, lead_days, transmission, color, compatible, source) values ('solar_screen', 'Solar screen · 5% openness', 'DEMO-FAB-102', 3.0, 90.0, 44.0, 5, 'Filtered light', 'Stone grey', array['motorized_roller','manual_roller']::text[], 'Demo warehouse · WH-002') on conflict (id) do nothing;
insert into public.inventory_materials (id, name, sku, roll_width_m, stock_lm, cost_per_lm, lead_days, transmission, color, compatible, source) values ('premium_blackout', 'Performance blackout', 'DEMO-FAB-103', 3.2, 120.0, 65.0, 4, 'Blackout', 'Soft white', array['motorized_roller','manual_roller','curtain']::text[], 'Demo warehouse · WH-003') on conflict (id) do nothing;
insert into public.manufacturing_settings (id, policy, scenarios, provenance, is_sample) values ('default', '{"labor_aed_hour": 45, "installation_aed_hour": 65, "margin_fraction": 0.3, "vat_fraction": 0.05, "waste_fraction": 0.08, "factory_hours_day": 6, "installation_hours_day": 6, "queue_business_days": 2, "source": "Demo estimating policy \u00b7 EST-001", "quality_business_days": 1, "working_weekdays": [0, 1, 2, 3, 4], "holidays": [], "currency": "AED", "quote_exclusions": ["Electrical work and power supply", "Scaffolding / special access", "Structural alterations", "Delivery charges and nonstandard hardware"]}'::jsonb, '[{"id": "shortage", "title": "The fabric shortfall", "category": "MATERIAL PLANNING", "description": "24 motorized blinds. Limited blackout stock. Find a viable alternative.", "deadline_days": 35, "request": {"customer": "Demo \u00b7 Meridian Workspace", "project_name": "Business Bay office fit-out", "brief": "Supply and install motorized blackout roller blinds for 24 office windows. Warm neutral finish, remote control and a clean fit. Check material availability and delivery feasibility before confirming the estimate.", "product": "motorized_roller", "fabric_id": "linen_blackout", "quantity": 24, "width_m": 1.8, "height_m": 2.4, "site": "Business Bay, Dubai"}}, {"id": "rush", "title": "The urgent fit-out", "category": "DELIVERY FEASIBILITY", "description": "A five-day deadline. Check the supply chain and realistic completion.", "deadline_days": 5, "request": {"customer": "Demo \u00b7 Meridian Workspace", "project_name": "Business Bay office fit-out", "brief": "Supply and install motorized blackout roller blinds for 24 office windows. Warm neutral finish, remote control and a clean fit. Check material availability and delivery feasibility before confirming the estimate.", "product": "motorized_roller", "fabric_id": "linen_blackout", "quantity": 24, "width_m": 1.8, "height_m": 2.4, "site": "Business Bay, Dubai"}}, {"id": "ready", "title": "The clear-to-review order", "category": "END-TO-END WORKFLOW", "description": "Available fabric and a flexible deadline. Prepare an estimate for review.", "deadline_days": 35, "request": {"customer": "Demo \u00b7 Meridian Workspace", "project_name": "Business Bay office fit-out", "brief": "Supply and install motorized blackout roller blinds for 24 office windows. Warm neutral finish, remote control and a clean fit. Check material availability and delivery feasibility before confirming the estimate.", "product": "motorized_roller", "fabric_id": "premium_blackout", "quantity": 24, "width_m": 1.8, "height_m": 2.4, "site": "Business Bay, Dubai"}}]'::jsonb, 'Synthetic interview seed data; replace with approved company records.', true) on conflict (id) do nothing;
insert into public.company_knowledge_settings (id, metadata) values ('default', '{"provenance": "Website text and links supplied by the user; pages were not independently fetched.", "source_kind": "user_supplied_website_copy", "captured_on": "2026-10-13", "categories": [{"id": "internal", "name": "Internal Shades", "description": "Blinds and curtains for residential and commercial interiors.", "source_url": "https://www.royalblinds.com/internal-shades/"}, {"id": "external", "name": "External Shades", "description": "Outdoor shading, architectural structures and outdoor furnishings.", "source_url": "https://www.royalblinds.com/external-shades/"}, {"id": "smart", "name": "Smart Solutions", "description": "Automation and controls that can accompany internal and external products; compatibility must be confirmed.", "source_url": "https://www.royalblinds.com/"}], "limitations": ["This content is company website copy supplied by the user, not independently verified engineering documentation.", "Product listings establish portfolio membership, not model-specific performance or compatibility.", "Generic wind, rain, heat, UV and insect protection claims do not establish a rating for every product.", "No motor model, torque, voltage, IP rating, smart-home protocol, app brand or device compatibility list was supplied.", "No current prices, component stock, bills of materials, warranties or installation manuals were supplied.", "Smart Solutions is an automation layer across applicable products, not confirmation that every listed product is motorized.", "Current estimating tools support roller blinds and manual-track curtains only; other products need technical and commercial assessment."]}'::jsonb) on conflict (id) do nothing;

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
