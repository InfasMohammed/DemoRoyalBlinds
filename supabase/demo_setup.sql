-- Run in the Supabase SQL editor for a dedicated demo project.
-- Creates the app's table and three complete synthetic report snapshots.
-- Existing reports (including approved seed reports) are preserved on reruns.
begin;

create table if not exists public.demo_reports (
  id uuid primary key,
  project_name text not null,
  status text not null check (status in ('blocked', 'awaiting_review', 'demo_approved')),
  payload jsonb not null,
  created_at timestamptz not null default now()
);
create index if not exists demo_reports_created_at_idx
  on public.demo_reports (created_at desc);
alter table public.demo_reports enable row level security;
revoke all on public.demo_reports from anon, authenticated;
grant select, insert, update on public.demo_reports to service_role;

do $seed$
declare
  sample record;
  as_of date := (now() at time zone 'Asia/Dubai')::date;
  d date;
  step integer;
  material_date date;
  factory_start date;
  factory_end date;
  qa_date date;
  install_start date;
  completion date;
  due date;
  required_lm numeric := round(24 * 2.65 * 1.08, 2);
  shortage numeric;
  direct_cost numeric;
  subtotal numeric;
  vat numeric;
  blockers text[];
  review_status text;
  req jsonb;
  requirements jsonb;
  fabric jsonb;
  materials jsonb;
  quality jsonb;
  costing jsonb;
  production jsonb;
  decision jsonb;
  traces jsonb;
  report jsonb;
begin
  for sample in
    select * from (values
      ('a1111111-1111-4111-8111-111111111111'::uuid,
       'Demo - Fabric shortage', 'linen_blackout', 'Linen-look blackout',
       'DEMO-FAB-101', 'Warm ivory', 28::numeric, 52::numeric, 7, 35),
      ('a2222222-2222-4222-8222-222222222222'::uuid,
       'Demo - Ready for review', 'premium_blackout', 'Performance blackout',
       'DEMO-FAB-103', 'Soft white', 120::numeric, 65::numeric, 4, 35),
      ('a3333333-3333-4333-8333-333333333333'::uuid,
       'Demo - Urgent office fit-out', 'premium_blackout', 'Performance blackout',
       'DEMO-FAB-103', 'Soft white', 120::numeric, 65::numeric, 4, 5)
    ) as fixtures(id, project_name, fabric_id, fabric_name, sku, color,
                  stock_lm, cost_per_lm, supplier_days, due_days)
  loop
    due := as_of + sample.due_days;
    shortage := greatest(0, required_lm - sample.stock_lm);
    blockers := array[]::text[];

    -- Match the Python demo calendar: Monday-Friday, two-day factory queue,
    -- three manufacturing days, one QA day, then two installation days.
    d := as_of + case when shortage > 0 then sample.supplier_days else 0 end;
    while extract(isodow from d) > 5 loop d := d + 1; end loop;
    material_date := d;
    for step in 1..7 loop
      d := d + 1;
      while extract(isodow from d) > 5 loop d := d + 1; end loop;
      case step
        when 2 then factory_start := d;
        when 4 then factory_end := d;
        when 5 then qa_date := d;
        when 6 then install_start := d;
        when 7 then completion := d;
        else null;
      end case;
    end loop;

    req := jsonb_build_object(
      'customer', 'Demo - Meridian Workspace', 'project_name', sample.project_name,
      'brief', 'Supply and install 24 motorized blackout roller blinds. Confirm fabric availability, price and delivery before approval.',
      'product', 'motorized_roller', 'fabric_id', sample.fabric_id,
      'quantity', 24, 'width_m', 1.8, 'height_m', 2.4,
      'due_date', due, 'site', 'Business Bay, Dubai'
    );
    requirements := jsonb_build_object(
      'product_name', 'Motorized roller blinds', 'area_sqm', 103.68,
      'dimensions', '1.8 x 2.4 m', 'quantity', 24,
      'scope', 'Supply, manufacture and installation; site survey required.',
      'source_of_truth', 'Structured form fields; brief is context only.'
    );
    fabric := jsonb_build_object(
      'id', sample.fabric_id, 'name', sample.fabric_name,
      'sku', sample.sku, 'color', sample.color, 'roll_width_m', 3.2,
      'stock_lm', sample.stock_lm, 'cost_per_lm', sample.cost_per_lm,
      'lead_days', sample.supplier_days, 'transmission', 'Blackout',
      'compatible', jsonb_build_array('motorized_roller', 'manual_roller', 'curtain'),
      'source', 'Synthetic warehouse fixture'
    );
    materials := jsonb_build_object(
      'fabric', fabric, 'required_lm', required_lm, 'shortage_lm', shortage,
      'in_stock', shortage = 0, 'fits_roll', true,
      'layout', '1 panel per roll row; 10 cm width and 25 cm length allowance',
      'waste_percent', 8, 'stock_reserved', false,
      'lead_days', case when shortage > 0 then sample.supplier_days else 0 end,
      'alternatives', case when shortage > 0 then jsonb_build_array(
        jsonb_build_object('id', 'premium_blackout', 'name', 'Performance blackout',
          'stock_lm', 120, 'reason', 'Same light-control category; confirm colour, specification and revised price.')
      ) else '[]'::jsonb end
    );
    quality := jsonb_build_object(
      'blockers', '[]'::jsonb, 'certification_verified', false,
      'note', 'Demo checklist only; it does not certify compliance.',
      'checklist', jsonb_build_array(
        'Survey every opening and confirm measurement tolerances.',
        'Approve the physical fabric sample and light-control specification.',
        'Inspect fabric defects and record batch traceability.',
        'Check finished dimensions, alignment and smooth operation.',
        'Verify fixing substrate, site access and installer safety plan.',
        'Qualified installer to verify power, motor load and wiring.',
        'Test motor limits, remote pairing and safe operation.'
      )
    );

    direct_cost := required_lm * sample.cost_per_lm + 24 * 85 + 24 * 245
                   + 13.2 * 45 + 9.6 * 65;
    subtotal := round(direct_cost / 0.70, 2);
    vat := round(subtotal * 0.05, 2);
    costing := jsonb_build_object(
      'currency', 'AED', 'direct_cost', direct_cost, 'subtotal', subtotal,
      'vat', vat, 'total', subtotal + vat,
      'gross_margin_percent', 30, 'vat_percent', 5, 'valid', true,
      'per_unit_incl_vat', round((subtotal + vat) / 24, 2),
      'note', 'Illustrative estimate using demo rates, subject to survey and commercial review.',
      'exclusions', jsonb_build_array('Electrical work and power supply',
        'Scaffolding / special access', 'Structural alterations',
        'Delivery charges and nonstandard hardware'),
      'lines', jsonb_build_array(
        jsonb_build_object('description', sample.fabric_name || ' fabric',
          'quantity', required_lm, 'unit', 'lm', 'unit_cost', sample.cost_per_lm,
          'cost', required_lm * sample.cost_per_lm),
        jsonb_build_object('description', 'Hardware assemblies', 'quantity', 24,
          'unit', 'units', 'unit_cost', 85, 'cost', 2040),
        jsonb_build_object('description', 'Motor and remote sets', 'quantity', 24,
          'unit', 'sets', 'unit_cost', 245, 'cost', 5880),
        jsonb_build_object('description', 'Manufacturing labour', 'quantity', 13.2,
          'unit', 'hours', 'unit_cost', 45, 'cost', 594),
        jsonb_build_object('description', 'Installation labour', 'quantity', 9.6,
          'unit', 'hours', 'unit_cost', 65, 'cost', 624)
      )
    );
    production := jsonb_build_object(
      'as_of', as_of, 'material_ready', material_date,
      'manufacture_start', factory_start, 'manufacture_end', factory_end,
      'quality_date', qa_date, 'installation_start', install_start,
      'completion_date', completion, 'due_date', due,
      'on_time', completion <= due, 'slack_days', due - completion,
      'factory_hours', 13.2, 'installation_hours', 9.6,
      'assumptions', jsonb_build_array(
        'Monday-Friday calendar; public holidays excluded.',
        'One factory cell and one installation team; 6 productive hours/day.',
        'Two business days existing queue, one QA day, then installation.',
        'Supplier lead times are calendar days and require confirmation.'
      )
    );
    if shortage > 0 then
      blockers := array_append(blockers, format('Resolve %s lm fabric shortage before approval.', shortage));
    end if;
    if completion > due then
      blockers := array_append(blockers, 'Completion exceeds the deadline; agree a feasible date or revise the specification.');
    end if;
    review_status := case when cardinality(blockers) > 0 then 'blocked' else 'awaiting_review' end;
    decision := jsonb_build_object(
      'status', review_status, 'blockers', to_jsonb(blockers),
      'headline', case when review_status = 'blocked'
        then 'Resolve constraints before approval' else 'Estimate ready for human review' end,
      'human_approval_required', true,
      'execution', 'No purchasing, stock reservation, dispatch or customer communication.',
      'actions', jsonb_build_array(
        'Resolve any stock shortfall using a customer-approved alternative and rerun.',
        'Confirm the proposed completion date with the customer.',
        'Arrange a site survey and verify all measurements.',
        'Review sample, scope, exclusions and commercial terms.'
      )
    );

    -- Seeded specialist-shaped evidence, not a live LangGraph/LLM run.
    select jsonb_agg(jsonb_build_object(
      'agent', t.agent, 'role', t.role, 'summary', t.summary,
      'recommendation', 'Synthetic SQL fixture; rerun analysis for current findings.',
      'sources', jsonb_build_array('Synthetic SQL seed data'),
      'facts', t.facts, 'mode', 'rules', 'duration_ms', 0
    ) order by t.seq) into traces
    from (values
      (1, 'Specification agent', 'Normalize the project scope', '24 motorized roller blinds; measurements remain provisional.', requirements),
      (2, 'Inventory agent', 'Calculate fabric and availability', format('%s lm required; %s lm shortfall.', required_lm, shortage), materials),
      (3, 'Quality & installation agent', 'Review limits and site checks', 'No specification blockers; site verification is required.', quality),
      (4, 'Quotation agent', 'Calculate the AED estimate', format('Illustrative total AED %s including VAT.', subtotal + vat), costing),
      (5, 'Production agent', 'Check capacity and delivery', format('Estimated completion: %s.', completion), production),
      (6, 'Coordinator', 'Apply the review gate', decision->>'headline', decision)
    ) as t(seq, agent, role, summary, facts);

    report := jsonb_build_object(
      'id', sample.id, 'created_at', now(), 'status', review_status,
      'data_mode', 'synthetic_demo', 'reasoning_mode', 'Seeded demo', 'elapsed_ms', 0,
      'seed_note', 'SQL fixture only. LangGraph and an LLM did not execute for this seeded report.',
      'request', req, 'requirements', requirements, 'materials', materials,
      'quality', quality, 'costing', costing, 'production', production,
      'decision', decision, 'traces', traces
    );
    insert into public.demo_reports (id, project_name, status, payload)
    values (sample.id, sample.project_name, review_status, report)
    on conflict (id) do nothing;
  end loop;
end;
$seed$;

commit;

-- Verify the three seeded examples, without selecting private report contents.
select project_name, status,
       payload #>> '{costing,total}' as estimate_aed,
       payload #>> '{materials,shortage_lm}' as fabric_shortage_lm,
       payload #>> '{production,completion_date}' as estimated_completion
from public.demo_reports
where id in (
  'a1111111-1111-4111-8111-111111111111'::uuid,
  'a2222222-2222-4222-8222-222222222222'::uuid,
  'a3333333-3333-4333-8333-333333333333'::uuid
)
order by project_name;
