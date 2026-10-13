-- Additive post-approval workflow. Run in the dedicated rbdemo database.
-- This feature is enabled only while manufacturing_settings.is_sample = true.
-- Existing reports, stock and settings are preserved; historical approvals are
-- not retroactively executed. New approvals explicitly authorize demo actions.
begin;
create table if not exists public.approval_jobs (
 report_id uuid primary key references public.demo_reports(id),
 status text not null check (status in ('queued','blocked','completed','cancelled')),
 reason text,
 agent_findings jsonb not null default '[]',
 updated_at timestamptz not null default now()
);
create table if not exists public.work_orders (
 id uuid primary key default gen_random_uuid(),
 report_id uuid not null unique references public.demo_reports(id),
 status text not null check (status in ('planned','in_production','awaiting_quality','ready_for_installation','completed','cancelled')),
 production_plan jsonb not null,
 created_at timestamptz not null default now()
);
create table if not exists public.material_reservations (
 report_id uuid primary key references public.demo_reports(id),
 material_id text not null references public.inventory_materials(id),
 quantity_lm numeric not null check (quantity_lm > 0),
 status text not null check (status in ('active','consumed','released')),
 created_at timestamptz not null default now()
);
create index if not exists material_reservations_active_idx on public.material_reservations(material_id) where status='active';
create table if not exists public.production_bookings (
 work_order_id uuid not null references public.work_orders(id),
 stage text not null check (stage in ('factory','installation')),
 work_date date not null,
 hours numeric not null check (hours > 0),
 released boolean not null default false,
 primary key(work_order_id,stage,work_date)
);
create index if not exists production_bookings_date_idx on public.production_bookings(stage,work_date) where not released;
create table if not exists public.work_order_tasks (
 id uuid primary key default gen_random_uuid(),
 work_order_id uuid not null references public.work_orders(id),
 stage text not null check (stage in ('manufacturing','quality','installation')),
 description text not null,
 status text not null default 'pending' check (status in ('pending','in_progress','completed','failed','cancelled')),
 unique(work_order_id,stage,description)
);
create table if not exists public.project_events (
 id bigint generated always as identity primary key,
 report_id uuid not null references public.demo_reports(id),
 event_type text not null,
 actor text not null,
 detail text not null,
 created_at timestamptz not null default now()
);
create index if not exists project_events_report_idx on public.project_events(report_id,id);
alter table public.approval_jobs enable row level security;
alter table public.work_orders enable row level security;
alter table public.material_reservations enable row level security;
alter table public.production_bookings enable row level security;
alter table public.work_order_tasks enable row level security;
alter table public.project_events enable row level security;
revoke all on public.approval_jobs,public.work_orders,public.material_reservations,public.production_bookings,public.work_order_tasks,public.project_events from anon,authenticated;
grant select,insert,update on public.approval_jobs,public.work_orders,public.material_reservations,public.production_bookings,public.work_order_tasks to service_role;
grant select,insert on public.project_events to service_role;
grant usage,select on sequence public.project_events_id_seq to service_role;

create or replace function public.get_execution_summary(p_report_id uuid)
returns jsonb language sql stable security invoker set search_path=public,pg_temp
as $f$
 select jsonb_build_object('status',j.status,'reason',j.reason,'agent_findings',j.agent_findings,
  'updated_at',j.updated_at,'work_order',
    (select to_jsonb(w) from public.work_orders w where w.report_id=j.report_id),
  'reservation',(select to_jsonb(r) from public.material_reservations r where r.report_id=j.report_id),
  'tasks',coalesce((select jsonb_agg(to_jsonb(t) order by t.stage,t.description) from public.work_order_tasks t join public.work_orders w on w.id=t.work_order_id where w.report_id=j.report_id),'[]'::jsonb),
  'bookings',coalesce((select jsonb_agg(to_jsonb(b) order by b.work_date,b.stage) from public.production_bookings b join public.work_orders w on w.id=b.work_order_id where w.report_id=j.report_id),'[]'::jsonb),
  'events',coalesce((select jsonb_agg(to_jsonb(e) order by e.id) from public.project_events e where e.report_id=j.report_id),'[]'::jsonb))
 from public.approval_jobs j where j.report_id=p_report_id;
$f$;

create or replace function public.get_operations_snapshot()
returns jsonb language sql stable security invoker set search_path=public,pg_temp
as $f$
 select jsonb_build_object(
  'products',(select jsonb_object_agg(p.id,to_jsonb(p)-'id'-'quality_checklist') from public.manufacturing_products p),
  'fabrics',(select jsonb_agg(to_jsonb(m)||jsonb_build_object(
    'on_hand_lm',m.stock_lm,'reserved_lm',coalesce(r.quantity,0),
    'stock_lm',greatest(0,m.stock_lm-coalesce(r.quantity,0))) order by m.id)
    from public.inventory_materials m left join
      (select material_id,sum(quantity_lm) quantity from public.material_reservations where status='active' group by material_id) r on r.material_id=m.id),
  'checklists',(select jsonb_object_agg(p.id,to_jsonb(p.quality_checklist)) from public.manufacturing_products p),
  'policy',s.policy,'scenarios',s.scenarios,'provenance',s.provenance,'is_sample',s.is_sample)
 from public.manufacturing_settings s where s.id='default';
$f$;

create or replace function public.approve_project(p_report_id uuid,p_approval jsonb)
returns jsonb language plpgsql security invoker set search_path=public,pg_temp
as $f$
declare r public.demo_reports%rowtype;
begin
 select * into r from public.demo_reports where id=p_report_id for update;
 if not found then return null; end if;
 if r.status='demo_approved' then return r.payload; end if;
 if r.status<>'awaiting_review' then raise exception 'This report has unresolved blockers.'; end if;
 if not coalesce((p_approval->>'measurements_confirmed')::boolean,false)
    or not coalesce((p_approval->>'specification_confirmed')::boolean,false)
    or not coalesce((p_approval->>'commercial_terms_confirmed')::boolean,false)
    or not coalesce((p_approval->>'execution_confirmed')::boolean,false)
    or length(trim(coalesce(p_approval->>'reviewer','')))<2 then
   raise exception 'All review and execution confirmations are required.';
 end if;
 if not coalesce((select is_sample from public.manufacturing_settings where id='default'),false) then
   raise exception 'Execution is restricted to the sample interview dataset.';
 end if;
 insert into public.approval_jobs(report_id,status) values(p_report_id,'queued');
 insert into public.project_events(report_id,event_type,actor,detail) values
   (p_report_id,'quotation_approved',p_approval->>'reviewer','Quotation approved; demo execution authorized and queued.');
 r.payload := r.payload || jsonb_build_object('status','demo_approved','approval',p_approval,'execution',public.get_execution_summary(p_report_id));
 update public.demo_reports set status='demo_approved',payload=r.payload where id=p_report_id;
 return r.payload;
end;
$f$;

create or replace function public.next_working_date(p_day date,p_policy jsonb)
returns date language plpgsql immutable security invoker set search_path=public,pg_temp
as $f$
begin
 if jsonb_typeof(p_policy->'working_weekdays')<>'array' or jsonb_array_length(p_policy->'working_weekdays')=0
    or exists(select 1 from jsonb_array_elements_text(p_policy->'working_weekdays') day where day::integer not between 0 and 6) then
   raise exception 'Invalid working calendar.';
 end if;
 while not (p_policy->'working_weekdays' @> to_jsonb(array[(extract(isodow from p_day)::integer-1)]))
    or p_policy->'holidays' @> to_jsonb(array[p_day::text]) loop
   p_day:=p_day+1;
 end loop;
 return p_day;
end;
$f$;
create or replace function public.add_working_dates(p_day date,p_days integer,p_policy jsonb)
returns date language plpgsql immutable security invoker set search_path=public,pg_temp
as $f$
declare i integer;
begin
 p_day:=public.next_working_date(p_day,p_policy);
 for i in 1..p_days loop p_day:=public.next_working_date(p_day+1,p_policy); end loop;
 return p_day;
end;
$f$;

create or replace function public.book_work_hours(p_order_id uuid,p_stage text,p_start date,p_hours numeric,p_capacity numeric,p_policy jsonb,p_due date)
returns date language plpgsql security invoker set search_path=public,pg_temp
as $f$
declare day date:=public.next_working_date(p_start,p_policy); remaining numeric:=p_hours; taken numeric; free numeric; allocated numeric;
begin
 if p_hours<=0 or p_capacity<=0 then raise exception 'Invalid planning hours or capacity.'; end if;
 while remaining>0 loop
   if day>p_due then raise exception 'Existing bookings leave insufficient capacity before the requested deadline.'; end if;
   select coalesce(sum(hours),0) into taken from public.production_bookings where stage=p_stage and work_date=day and not released;
   free:=greatest(0,p_capacity-taken);
   if free>0 then
     allocated:=least(remaining,free);
     insert into public.production_bookings(work_order_id,stage,work_date,hours) values(p_order_id,p_stage,day,allocated);
     remaining:=remaining-allocated;
   end if;
   if remaining>0 then day:=public.next_working_date(day+1,p_policy); end if;
 end loop;
 return day;
end;
$f$;

create or replace function public.execute_approved_project(p_report_id uuid,p_plan jsonb,p_findings jsonb)
returns jsonb language plpgsql security invoker set search_path=public,pg_temp
as $f$
declare r public.demo_reports%rowtype; j public.approval_jobs%rowtype; m public.inventory_materials%rowtype;
 s public.manufacturing_settings%rowtype; p public.manufacturing_products%rowtype;
 needed numeric; reserved numeric; v_reason text; order_id uuid; start_date date; factory_end date; quality_day date; install_end date; task text; final_plan jsonb;
begin
 -- Global settings lock serializes capacity allocation. All execution/progress
 -- transactions acquire this lock first, then report/order/material locks.
 select * into s from public.manufacturing_settings where id='default' for update;
 select * into r from public.demo_reports where id=p_report_id for update;
 if not found then return null; end if;
 select * into j from public.approval_jobs where report_id=p_report_id for update;
 if not found then raise exception 'This approval predates the execution workflow. Analyze and approve a new report.'; end if;
 if j.status in ('completed','cancelled') then return r.payload; end if;
 if r.status<>'demo_approved' or not coalesce((r.payload->'approval'->>'execution_confirmed')::boolean,false) then raise exception 'Human approval and execution authorization are required.'; end if;
 select * into m from public.inventory_materials where id=r.payload->'request'->>'fabric_id' for update;
 select * into p from public.manufacturing_products where id=r.payload->'request'->>'product' for share;
 needed:=(r.payload->'materials'->>'required_lm')::numeric;
 select coalesce(sum(quantity_lm),0) into reserved from public.material_reservations where material_id=m.id and status='active';
 if not s.is_sample then v_reason:='Execution is restricted to the sample interview dataset.';
 elsif r.payload->'data_snapshot'->>'data_source' is distinct from 'supabase' then v_reason:='Analyze a new quotation using Supabase business data before execution.';
 elsif r.payload->'data_snapshot' is null then v_reason:='This report has no business snapshot. Analyze and approve a new report.';
 elsif needed is null or needed<=0 or m.id is null or p.id is null then v_reason:='The approved material or product is missing or invalid.';
 elsif (to_jsonb(p)-'id'-'quality_checklist'-'updated_at') is distinct from (r.payload->'data_snapshot'->'products'->p.id)
   or to_jsonb(p.quality_checklist) is distinct from (r.payload->'data_snapshot'->'checklists'->p.id)
   or s.policy is distinct from (r.payload->'data_snapshot'->'policy')
   or (to_jsonb(m)-'updated_at'-'stock_lm') is distinct from ((r.payload->'materials'->'fabric')-'stock_lm'-'on_hand_lm'-'reserved_lm') then
   v_reason:='Product specifications, rates or planning settings changed. Analyze and approve a fresh quotation.';
 elsif m.stock_lm-reserved<needed then v_reason:='Available material is insufficient after existing reservations. Replenish or approve a revised specification.';
 end if;
 if v_reason is null then
  begin
   -- Tentative records are rolled back together if capacity is unavailable.
   insert into public.work_orders(report_id,status,production_plan) values(p_report_id,'planned',p_plan) returning id into order_id;
   insert into public.material_reservations(report_id,material_id,quantity_lm,status) values(p_report_id,m.id,needed,'active');
   start_date:=greatest((p_plan->>'manufacture_start')::date,public.add_working_dates((now() at time zone 'Asia/Dubai')::date,(s.policy->>'queue_business_days')::integer,s.policy));
   factory_end:=public.book_work_hours(order_id,'factory',start_date,(p_plan->>'factory_hours')::numeric,(s.policy->>'factory_hours_day')::numeric,s.policy,(r.payload->'request'->>'due_date')::date);
   quality_day:=public.add_working_dates(factory_end,(s.policy->>'quality_business_days')::integer,s.policy);
   install_end:=public.book_work_hours(order_id,'installation',public.add_working_dates(quality_day,1,s.policy),(p_plan->>'installation_hours')::numeric,(s.policy->>'installation_hours_day')::numeric,s.policy,(r.payload->'request'->>'due_date')::date);
   final_plan:=p_plan||jsonb_build_object(
      'manufacture_start',(select min(work_date) from public.production_bookings where work_order_id=order_id and stage='factory'),
      'manufacture_end',factory_end,'quality_date',quality_day,
      'installation_start',(select min(work_date) from public.production_bookings where work_order_id=order_id and stage='installation'),
      'completion_date',install_end,'on_time',true,'slack_days',(r.payload->'request'->>'due_date')::date-install_end);
   update public.work_orders set production_plan=final_plan where id=order_id;
   insert into public.work_order_tasks(work_order_id,stage,description) values(order_id,'manufacturing','Manufacture the approved openings and record finished dimensions.'),(order_id,'installation','Install at the approved site and record customer handover.');
   foreach task in array p.quality_checklist loop
    insert into public.work_order_tasks(work_order_id,stage,description) values(order_id,'quality',task);
   end loop;
   update public.approval_jobs set status='completed',reason=null,agent_findings=p_findings,updated_at=now() where report_id=p_report_id;
   insert into public.project_events(report_id,event_type,actor,detail) values(p_report_id,'work_order_created','Post-approval workflow','Material reserved; capacity booked; manufacturing, quality and installation tasks created.');
  exception when raise_exception then v_reason:=SQLERRM;
  end;
 end if;
 if v_reason is not null then
  update public.approval_jobs set status='blocked',reason=v_reason,agent_findings=p_findings,updated_at=now() where report_id=p_report_id;
  if j.status<>'blocked' or j.reason is distinct from v_reason then
   insert into public.project_events(report_id,event_type,actor,detail) values(p_report_id,'execution_blocked','Post-approval workflow',v_reason);
  end if;
 end if;
 update public.demo_reports set payload=payload||jsonb_build_object('execution',public.get_execution_summary(p_report_id)) where id=p_report_id returning payload into r.payload;
 return r.payload;
end;
$f$;

create or replace function public.advance_work_order(p_report_id uuid,p_action text,p_actor text,p_note text default '',p_checked_ids uuid[] default '{}')
returns jsonb language plpgsql security invoker set search_path=public,pg_temp
as $f$
declare r public.demo_reports%rowtype; w public.work_orders%rowtype; m public.inventory_materials%rowtype; reservation public.material_reservations%rowtype; is_sample boolean; held numeric; new_status text;
begin
 select s.is_sample into is_sample from public.manufacturing_settings s where id='default' for update;
 if not coalesce(is_sample,false) then raise exception 'Progress actions are restricted to the sample interview dataset.'; end if;
 if length(trim(coalesce(p_actor,'')))<2 then raise exception 'An operator name is required.'; end if;
 select * into r from public.demo_reports where id=p_report_id for update;
 if not found then return null; end if;
 select * into w from public.work_orders where report_id=p_report_id for update;
 if not found then raise exception 'No work order is ready. Resolve execution blockers first.'; end if;
 select * into reservation from public.material_reservations where report_id=p_report_id for update;
 select * into m from public.inventory_materials where id=reservation.material_id for update;
 -- Repeated progress requests are harmless, including lost-response retries.
 if p_action='start_production' and w.status in ('in_production','awaiting_quality','ready_for_installation','completed')
 or p_action='finish_production' and w.status in ('awaiting_quality','ready_for_installation','completed')
 or p_action='pass_quality' and w.status in ('ready_for_installation','completed')
 or p_action='complete_installation' and w.status='completed'
 or p_action='cancel' and w.status='cancelled' then return r.payload; end if;
 if p_action='start_production' and w.status='planned' then
  select coalesce(sum(quantity_lm),0) into held from public.material_reservations where material_id=m.id and status='active';
  if m.stock_lm<held then raise exception 'Recorded stock is below active reservations. Reconcile stock before production.'; end if;
  new_status:='in_production';
  update public.work_order_tasks set status='in_progress' where work_order_id=w.id and stage='manufacturing';
 elsif p_action='finish_production' and w.status='in_production' then
  select coalesce(sum(quantity_lm),0) into held from public.material_reservations where material_id=m.id and status='active';
  if reservation.status<>'active' or m.stock_lm<held then raise exception 'Material reservation cannot be consumed. Reconcile stock first.'; end if;
  update public.inventory_materials set stock_lm=stock_lm-reservation.quantity_lm where id=m.id;
  update public.material_reservations set status='consumed' where report_id=p_report_id;
  update public.work_order_tasks set status='completed' where work_order_id=w.id and stage='manufacturing';
  new_status:='awaiting_quality';
 elsif p_action='pass_quality' and w.status='awaiting_quality' then
  if exists(select 1 from public.work_order_tasks where work_order_id=w.id and stage='quality' and not (id=any(p_checked_ids))) then raise exception 'Every quality check must be confirmed.'; end if;
  if exists(select 1 from unnest(p_checked_ids) checked where not exists(select 1 from public.work_order_tasks t where t.id=checked and t.work_order_id=w.id and t.stage='quality')) then raise exception 'Unknown quality check.'; end if;
  update public.work_order_tasks set status='completed' where work_order_id=w.id and stage='quality';
  new_status:='ready_for_installation';
 elsif p_action='fail_quality' and w.status='awaiting_quality' then
  if length(trim(coalesce(p_note,'')))<5 then raise exception 'Record the quality issue before placing a hold.'; end if;
  update public.work_order_tasks set status='failed' where work_order_id=w.id and stage='quality';
  new_status:='awaiting_quality';
 elsif p_action='complete_installation' and w.status='ready_for_installation' then
  update public.work_order_tasks set status='completed' where work_order_id=w.id and stage='installation';
  new_status:='completed';
 elsif p_action='cancel' and w.status in ('planned','awaiting_quality','ready_for_installation') then
  if length(trim(coalesce(p_note,'')))<5 then raise exception 'Record a cancellation reason.'; end if;
  update public.material_reservations set status='released' where report_id=p_report_id and status='active';
  update public.production_bookings set released=true where work_order_id=w.id and (reservation.status='active' or stage='installation');
  update public.work_order_tasks set status='cancelled' where work_order_id=w.id and status<>'completed';
  update public.approval_jobs set status='cancelled',updated_at=now() where report_id=p_report_id;
  new_status:='cancelled';
 else raise exception 'This action does not match the current work-order stage.';
 end if;
 update public.work_orders set status=new_status where id=w.id;
 update public.approval_jobs set updated_at=now() where report_id=p_report_id;
 insert into public.project_events(report_id,event_type,actor,detail) values(p_report_id,p_action,p_actor,coalesce(p_note,''));
 update public.demo_reports set payload=payload||jsonb_build_object('execution',public.get_execution_summary(p_report_id)) where id=p_report_id returning payload into r.payload;
 return r.payload;
end;
$f$;

revoke all on function public.get_execution_summary(uuid),public.approve_project(uuid,jsonb),public.next_working_date(date,jsonb),public.add_working_dates(date,integer,jsonb),public.book_work_hours(uuid,text,date,numeric,numeric,jsonb,date),public.execute_approved_project(uuid,jsonb,jsonb),public.advance_work_order(uuid,text,text,text,uuid[]) from public,anon,authenticated;
grant execute on function public.get_execution_summary(uuid),public.approve_project(uuid,jsonb),public.next_working_date(date,jsonb),public.add_working_dates(date,integer,jsonb),public.book_work_hours(uuid,text,date,numeric,numeric,jsonb,date),public.execute_approved_project(uuid,jsonb,jsonb),public.advance_work_order(uuid,text,text,text,uuid[]) to service_role;
commit;
