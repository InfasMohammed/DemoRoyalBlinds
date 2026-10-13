-- Run in a dedicated demo Supabase project's SQL editor.
-- Synthetic reports only. Keep the service_role key on the trusted FastAPI server.
create table if not exists public.demo_reports (
  id uuid primary key,
  project_name text not null,
  status text not null check (status in ('blocked', 'awaiting_review', 'demo_approved')),
  payload jsonb not null,
  created_at timestamptz not null default now()
);
create index if not exists demo_reports_created_at_idx on public.demo_reports(created_at desc);
alter table public.demo_reports enable row level security;
-- Deliberately no anon/authenticated policies. Backend service_role access only.
revoke all on public.demo_reports from anon, authenticated;
grant select, insert, update on public.demo_reports to service_role;
comment on table public.demo_reports is 'Interview demonstration; contains synthetic project estimates, never operational orders.';
