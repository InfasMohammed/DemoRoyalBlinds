"""Rebuild the additive Supabase migration from the reviewed bundled corpus."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.knowledge import CHUNKS, DATA


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def export_sql():
    sql = """-- Generated from backend/app/data/company_knowledge.json.
-- User-supplied website copy; no technical approvals or verified live stock.
-- Run after demo_setup.sql (independent of the report table).
begin;
create extension if not exists vector with schema extensions;

create table if not exists public.company_products (
  id text primary key,
  name text not null,
  category text not null check (category in ('internal', 'external')),
  source_url text not null,
  quote_products jsonb not null default '[]'::jsonb
);

create table if not exists public.company_knowledge_chunks (
  id text primary key,
  document_id text not null,
  title text not null,
  heading text not null,
  category text not null check (category in ('internal', 'external', 'smart', 'company')),
  product_ids text[] not null default '{}',
  content text not null,
  source_url text not null,
  source_kind text not null,
  captured_on date not null,
  embedding extensions.vector(1536),
  embedding_model text
);
create index if not exists company_knowledge_category_idx
  on public.company_knowledge_chunks(category);
alter table public.company_products enable row level security;
alter table public.company_knowledge_chunks enable row level security;
revoke all on public.company_products, public.company_knowledge_chunks from anon, authenticated;
grant select, insert, update on public.company_products, public.company_knowledge_chunks to service_role;

"""
    product_rows = []
    for p in DATA['products']:
        product_rows.append('(' + ', '.join([literal(p['id']), literal(p['name']), literal(p['category']),
                                            literal(p['source_url']), literal(json.dumps(p['quote_products'])) + '::jsonb']) + ')')
    sql += 'insert into public.company_products (id, name, category, source_url, quote_products) values\n'
    sql += ',\n'.join(product_rows)
    sql += '\non conflict (id) do nothing;\n\n'
    chunk_rows = []
    for c in CHUNKS:
        ids = 'array[' + ','.join(literal(i) for i in c['product_ids']) + ']::text[]'
        values = [literal(c[key]) for key in ('id', 'document_id', 'title', 'heading', 'category')]
        values += [ids] + [literal(c[key]) for key in ('content', 'source_url', 'source_kind')]
        values += [literal(DATA['captured_on']) + '::date']
        chunk_rows.append('(' + ', '.join(values) + ')')
    sql += 'insert into public.company_knowledge_chunks (id, document_id, title, heading, category, product_ids, content, source_url, source_kind, captured_on) values\n'
    sql += ',\n'.join(chunk_rows)
    sql += """
on conflict (id) do nothing;

-- Preserve database edits on reruns. Changed text invalidates old embeddings.
create or replace function public.clear_changed_knowledge_embedding()
returns trigger language plpgsql set search_path = public, pg_temp
as $trigger$
begin
  if new.content is distinct from old.content then
    new.embedding := null;
    new.embedding_model := null;
  end if;
  return new;
end;
$trigger$;
drop trigger if exists knowledge_content_changed on public.company_knowledge_chunks;
create trigger knowledge_content_changed before update on public.company_knowledge_chunks
for each row execute function public.clear_changed_knowledge_embedding();

create or replace function public.match_company_knowledge(
  query_embedding extensions.vector(1536),
  filter_category text default null,
  filter_product text default null,
  match_count integer default 4
)
returns table (id text, content text, similarity double precision)
language sql stable security invoker
set search_path = public, extensions
as $function$
  select c.id, c.content,
         1 - (c.embedding operator(extensions.<=>) query_embedding) as similarity
  from public.company_knowledge_chunks c
  where c.embedding is not null
    and c.embedding_model = 'text-embedding-3-small'
    and (filter_category is null or c.category = filter_category)
    and (filter_product is null or cardinality(c.product_ids) = 0
         or filter_product = any(c.product_ids))
  order by c.embedding operator(extensions.<=>) query_embedding
  limit greatest(1, least(coalesce(match_count, 4), 10));
$function$;
revoke all on function public.match_company_knowledge(extensions.vector, text, text, integer) from public;
grant execute on function public.match_company_knowledge(extensions.vector, text, text, integer) to service_role;
commit;

-- Populated source text is searchable locally immediately. Vector embeddings
-- remain NULL until backend/scripts/index_knowledge.py succeeds with credentials.
select category, count(*) as passages, count(embedding) as embedded_passages
from public.company_knowledge_chunks group by category order by category;
"""
    return sql


if __name__ == '__main__':
    output = Path(__file__).resolve().parents[2] / 'supabase' / 'knowledge_base.sql'
    output.write_text(export_sql())
    print(f'Exported {len(DATA["products"])} products and {len(CHUNKS)} source passages to {output.name}.')
