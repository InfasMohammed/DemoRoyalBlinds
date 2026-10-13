-- Full additive setup. Preserve existing reports and edited business records.
begin;
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

-- Generated from backend/app/data/company_knowledge.json.
-- User-supplied website copy; no technical approvals or verified live stock.
-- Run after demo_setup.sql (independent of the report table).

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

insert into public.company_products (id, name, category, source_url, quote_products) values
('roller_blinds', 'Roller Blinds', 'internal', 'https://royalblinds.com/internal-shades/roller-blinds/', '["manual_roller", "motorized_roller"]'::jsonb),
('venetian_blinds', 'Venetian Blinds', 'internal', 'https://royalblinds.com/internal-shades/venetian-blinds/', '[]'::jsonb),
('wooden_blinds', 'Wooden Blinds', 'internal', 'https://royalblinds.com/internal-shades/wooden-blinds/', '[]'::jsonb),
('vertical_blinds', 'Vertical Blinds', 'internal', 'https://royalblinds.com/internal-shades/vertical-blinds/', '[]'::jsonb),
('roman_blinds', 'Roman Blinds', 'internal', 'https://royalblinds.com/internal-shades/roman-blinds/', '[]'::jsonb),
('zebra_roller_blinds', 'Zebra Roller Blinds', 'internal', 'https://royalblinds.com/internal-shades/zebra-roller-blinds/', '[]'::jsonb),
('curtains', 'Curtains', 'internal', 'https://royalblinds.com/internal-shades/curtains/', '["curtain"]'::jsonb),
('cubicle_curtains', 'Cubicle Curtains', 'internal', 'https://royalblinds.com/internal-shades/cubicle-curtains/', '[]'::jsonb),
('car_parking_shades', 'Car Parking Shades', 'external', 'https://royalblinds.com/external-shades/car-parking-shades/', '[]'::jsonb),
('sail_shades', 'Sail Shades', 'external', 'https://royalblinds.com/external-shades/sail-shades/', '[]'::jsonb),
('bioclimatic_pergolas', 'Bioclimatic Pergolas', 'external', 'https://royalblinds.com/external-shades/bioclimatic-pergolas/', '[]'::jsonb),
('tensile_shade_structures', 'Tensile Shade Structures', 'external', 'https://royalblinds.com/external-shades/tensile-shade-structures/', '[]'::jsonb),
('awnings', 'Awnings', 'external', 'https://royalblinds.com/external-shades/awnings/', '[]'::jsonb),
('outdoor_furniture', 'Outdoor Furniture', 'external', 'https://royalblinds.com/external-shades/outdoor-furniture/', '[]'::jsonb),
('umbrellas', 'Umbrellas', 'external', 'https://royalblinds.com/external-shades/umbrellas/', '[]'::jsonb)
on conflict (id) do nothing;

insert into public.company_knowledge_chunks (id, document_id, title, heading, category, product_ids, content, source_url, source_kind, captured_on) values
('RB-INTERNAL-01', 'RB-INTERNAL', 'Internal Shades — portfolio', 'Interior applications', 'internal', array[]::text[], 'Transform your home''s interior with the exquisite collection of blinds and curtains from Royal Blinds LLC, available in Dubai and Abu Dhabi. Our internal shades blend functionality with comfort, adding a stylish touch to any room. With a diverse range of designs—modern, traditional, simple, and sleek, we ensure a perfect fit for every style. Our window blinds elevate the ambiance of your home or office, providing both comfort and style. With a vast collection of customizable internal shades and curtains, we cater to your specific preferences.', 'https://www.royalblinds.com/internal-shades/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-INTERNAL-02', 'RB-INTERNAL', 'Internal Shades — portfolio', 'Internal product range', 'internal', array[]::text[], 'Explore our extensive range of blinds, including Roller Blinds, Venetian Blinds, Wooden Blinds, Vertical Blinds, Roman Blinds, and Zebra Blinds, available in both motorized and manual versions. Experience a welcoming atmosphere with our beautifully designed blinds. If you seek made-to-measure internal shades in Dubai to refresh your home, we are the premier manufacturers and suppliers, delivering top-quality shades across the UAE. The supplied Types of Internal Shades listing also includes Curtains and Cubicle Curtains.', 'https://www.royalblinds.com/internal-shades/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-INTERNAL-03', 'RB-INTERNAL', 'Internal Shades — portfolio', 'Made-to-measure interiors', 'internal', array[]::text[], 'As the demand for blinds grows for both commercial and residential use, our products stand out with their beautiful designs, quality fabrics, and reliable technologies. Elevate your interiors and enhance your comfort with the exceptional blinds and curtains from Royal Blinds LLC.', 'https://www.royalblinds.com/internal-shades/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-EXTERNAL-01', 'RB-EXTERNAL', 'External Shades — applications and portfolio', 'Outdoor applications', 'external', array[]::text[], 'Transform your outdoor spaces with Royal Blinds'' top-of-the-line external blinds and shades, designed to protect you and your belongings from wind, rain, sun, and insects. Our products not only enhance the aesthetic appeal of your home but also provide essential functionality. Protect your furniture from dirt and dust, and enjoy the added security of side-welded zips that lock the fabric firmly into side tracks, creating the perfect outdoor sanctuary for BBQ areas, patios, balconies, front porches, and windows.', 'https://www.royalblinds.com/external-shades/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-EXTERNAL-02', 'RB-EXTERNAL', 'External Shades — applications and portfolio', 'Membrane shade structures', 'external', array[]::text[], 'Experience the highest quality fabric structures and expert craftsmanship with our custom-made tension membrane shade sails and structures. Ideal for commercial and residential applications, these shades are perfect for schools, playgrounds, swimming pools, sporting venues, shop facades, shopping centers, car parks, clubs, hotels, walkways, villas, and patios. Our reputation for delivering first-class structures and continuously developing designs to meet client needs sets us apart in the industry.', 'https://www.royalblinds.com/external-shades/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-EXTERNAL-03', 'RB-EXTERNAL', 'External Shades — applications and portfolio', 'External product range', 'external', array[]::text[], 'Enhance your outdoor living with our retractable shades, tensile shades, pergolas, awnings, and other exterior shade products. Made from durable, long-lasting fabric, our blinds withstand the elements and are easy to maintain. Our Screeny Horizontal Blinds provide excellent shade for outdoor areas, windows, decks, and patios. We also offer stunning canopies in various shapes, colors, and sizes tailored to outdoor applications in the UAE. The supplied Types of External Shades listing includes Car Parking Shades, Sail Shades, Bioclimatic Pergolas, Tensile Shade Structures, Awnings, Outdoor Furniture and Umbrellas.', 'https://www.royalblinds.com/external-shades/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-EXTERNAL-04', 'RB-EXTERNAL', 'External Shades — applications and portfolio', 'Commercial awnings and shutters', 'external', array[]::text[], 'For commercial-style awnings, we supply fully wind-rated options that are architecturally designed, technologically advanced, and simple to use. Made in Italy with international certifications and patents, these designer awnings blend innovative style and technique, suitable for both classic and modern architecture. In addition to external shade products, we offer high-quality aluminum roller shutter covers for doors and windows in three systems: electric motorized, manual, and electric motorized with manual control.', 'https://www.royalblinds.com/external-shades/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-EXTERNAL-05', 'RB-EXTERNAL', 'External Shades — applications and portfolio', 'Heat filtering and customisation', 'external', array[]::text[], 'Our external shades are engineered to keep your space cool during summers by reflecting heat and filtering wind, making them an excellent choice for energy savings. The versatile designs, themes, patterns, materials, and colors ensure they complement any setting. These are category-level marketing statements; no quantified energy savings, test reports or model-specific performance data were supplied.', 'https://www.royalblinds.com/external-shades/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-SMART-01', 'RB-SMART', 'Smart Solutions — automation and control', 'Integrated automation', 'smart', array[]::text[], 'Unique solutions, blending technology, innovation, quality, and design. Automation and control systems for awnings, blinds, curtains and skylight now with integrated management through smart intuitive interfaces: practical, functional and elegant solutions for the ideal way to live in every space.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-SMART-02', 'RB-SMART', 'Smart Solutions — automation and control', 'Remote and smartphone operation', 'smart', array[]::text[], 'Motorized Blinds and Shades are usually operated by remote control. To allow you total control of your blinds when you are at home or away you can even add a Smartphone control functionality that provides you with the same comfortable shading of a roller blind, but with the convenience of having full control at your fingertips.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-SMART-03', 'RB-SMART', 'Smart Solutions — automation and control', 'Roller blind power options', 'smart', array[]::text[], 'With a huge selection of fabrics and designs to choose from, our Smart Solutions are the ideal choice in terms of the technology behind the aesthetics. Driven by an integrated motor that is hidden from sight, our motorized roller blinds can be powered by a rechargeable battery or directly from your mains supply.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-SMART-04', 'RB-SMART', 'Smart Solutions — automation and control', 'Design and installation support', 'smart', array[]::text[], 'Architects, Designers and Engineers find their ideal partner in Royal Blinds, always ready to provide complete support during project design, installation and implementation.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-SMART-05', 'RB-SMART', 'Smart Solutions — automation and control', 'Unnamed Solution 1', 'smart', array[]::text[], 'One of the most preferred blinds for both commercial and residential spaces. Our manufacturing process does not involve the use of adhesives or sewing to produce clean and professionally finished blinds. The supplied copy labels this only Solution 1; its exact product/model is not identified.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-SMART-06', 'RB-SMART', 'Smart Solutions — automation and control', 'Solution 2 — Venetian blinds', 'smart', array[]::text[], 'Custom crafted Venetian Blinds, in a variety of exciting colors, are engineered with durability to give a dependable and longer trouble-free performance. Our raw materials and motors are imported from the USA and Europe.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-SMART-07', 'RB-SMART', 'Smart Solutions — automation and control', 'Reported privacy and light-control benefits', 'smart', array[]::text[], 'The supplied Smart Solutions copy describes privacy and reduced sunlight, dust and pollutants, and claims UV and IR protection for sun shades and drapes. No numerical light transmission, UV/IR ratings or test reports were supplied. These marketing benefits must not be treated as universal protection guarantees or verified performance for every product.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-COMPANY-01', 'RB-COMPANY', 'Royal Blinds — company profile', 'Company background', 'company', array[]::text[], 'Established in 1989 in Dubai, UAE, and wholly owned by the Al Jallaf Family, Royal Blinds has garnered recognition as a One Stop Centre for innovative, meticulously designed, and expertly installed internal and external shades. Royal Blinds is affiliated with the Dubai Chamber of Commerce and Abu Dhabi Chamber of Commerce. It supplies property developers and contractors and provides consultations to architecture and design firms.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-COMPANY-02', 'RB-COMPANY', 'Royal Blinds — company profile', 'Production and regional presence', 'company', array[]::text[], 'With our expansive 124,800 square feet production unit located in Dubai''s Al Quoz industrial area, alongside a branch in Abu Dhabi and dedicated business channels across the Gulf States, we ensure seamless fulfillment of diverse client needs. The supplied milestone timeline records expansion into Kuwait, Bahrain, Saudi and Oman in 2008 and establishment of the External Shades section in 2005.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-COMPANY-03', 'RB-COMPANY', 'Royal Blinds — company profile', 'Reported certifications', 'company', array[]::text[], 'The supplied website copy reports ISO-QMS-9001, ISO-EMS-14001 and OHSAS 18001 certifications. No certificate numbers, current certificates, expiry dates or product-specific certification documents were supplied.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-COMPANY-04', 'RB-COMPANY', 'Royal Blinds — company profile', 'Contact and locations', 'company', array[]::text[], 'Dubai: head office, showroom and factory. Abu Dhabi: office and showroom. Contact email: info@royalblinds.com. Dubai telephone: +971 4 347 4760. Abu Dhabi telephone: +971 2 555 7393.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-COMPANY-05', 'RB-COMPANY', 'Royal Blinds — company profile', 'Company milestones and website counters', 'company', array[]::text[], 'The supplied timeline lists: inception in 1989; Al Quoz premises in 1990; high-profile projects in 1997; fire recovery and premise expansion in 1998; manufacturing plant in 1999; 100 employees in 2001; External Shades section in 2005; Gulf expansion in 2008; CSR initiatives in 2015; 30th anniversary in 2019. Supplied counters report 50+ Projects Launched, 10000+ Happy Clients and 43+ Worldwide Partners, with more than 43 partners in over 20 countries. The project-counter explanation refers to 49 new projects in 2019. These historical marketing figures are not independently verified current operating metrics.', 'https://www.royalblinds.com/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-roller_blinds', 'RB-PRODUCT-roller_blinds', 'Roller Blinds', 'Product listing', 'internal', array['roller_blinds']::text[], 'The supplied internal shades listing includes Roller Blinds and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/internal-shades/roller-blinds/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-venetian_blinds', 'RB-PRODUCT-venetian_blinds', 'Venetian Blinds', 'Product listing', 'internal', array['venetian_blinds']::text[], 'The supplied internal shades listing includes Venetian Blinds and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/internal-shades/venetian-blinds/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-wooden_blinds', 'RB-PRODUCT-wooden_blinds', 'Wooden Blinds', 'Product listing', 'internal', array['wooden_blinds']::text[], 'The supplied internal shades listing includes Wooden Blinds and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/internal-shades/wooden-blinds/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-vertical_blinds', 'RB-PRODUCT-vertical_blinds', 'Vertical Blinds', 'Product listing', 'internal', array['vertical_blinds']::text[], 'The supplied internal shades listing includes Vertical Blinds and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/internal-shades/vertical-blinds/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-roman_blinds', 'RB-PRODUCT-roman_blinds', 'Roman Blinds', 'Product listing', 'internal', array['roman_blinds']::text[], 'The supplied internal shades listing includes Roman Blinds and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/internal-shades/roman-blinds/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-zebra_roller_blinds', 'RB-PRODUCT-zebra_roller_blinds', 'Zebra Roller Blinds', 'Product listing', 'internal', array['zebra_roller_blinds']::text[], 'The supplied internal shades listing includes Zebra Roller Blinds and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/internal-shades/zebra-roller-blinds/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-curtains', 'RB-PRODUCT-curtains', 'Curtains', 'Product listing', 'internal', array['curtains']::text[], 'The supplied internal shades listing includes Curtains and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/internal-shades/curtains/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-cubicle_curtains', 'RB-PRODUCT-cubicle_curtains', 'Cubicle Curtains', 'Product listing', 'internal', array['cubicle_curtains']::text[], 'The supplied internal shades listing includes Cubicle Curtains and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/internal-shades/cubicle-curtains/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-car_parking_shades', 'RB-PRODUCT-car_parking_shades', 'Car Parking Shades', 'Product listing', 'external', array['car_parking_shades']::text[], 'The supplied external shades listing includes Car Parking Shades and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/external-shades/car-parking-shades/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-sail_shades', 'RB-PRODUCT-sail_shades', 'Sail Shades', 'Product listing', 'external', array['sail_shades']::text[], 'The supplied external shades listing includes Sail Shades and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/external-shades/sail-shades/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-bioclimatic_pergolas', 'RB-PRODUCT-bioclimatic_pergolas', 'Bioclimatic Pergolas', 'Product listing', 'external', array['bioclimatic_pergolas']::text[], 'The supplied external shades listing includes Bioclimatic Pergolas and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/external-shades/bioclimatic-pergolas/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-tensile_shade_structures', 'RB-PRODUCT-tensile_shade_structures', 'Tensile Shade Structures', 'Product listing', 'external', array['tensile_shade_structures']::text[], 'The supplied external shades listing includes Tensile Shade Structures and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/external-shades/tensile-shade-structures/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-awnings', 'RB-PRODUCT-awnings', 'Awnings', 'Product listing', 'external', array['awnings']::text[], 'The supplied external shades listing includes Awnings and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/external-shades/awnings/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-outdoor_furniture', 'RB-PRODUCT-outdoor_furniture', 'Outdoor Furniture', 'Product listing', 'external', array['outdoor_furniture']::text[], 'The supplied external shades listing includes Outdoor Furniture and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/external-shades/outdoor-furniture/', 'user_supplied_website_copy', '2026-10-13'::date),
('RB-PRODUCT-umbrellas', 'RB-PRODUCT-umbrellas', 'Umbrellas', 'Product listing', 'external', array['umbrellas']::text[], 'The supplied external shades listing includes Umbrellas and links to this product page. Product-specific page text and technical specifications have not been supplied.', 'https://royalblinds.com/external-shades/umbrellas/', 'user_supplied_website_copy', '2026-10-13'::date)
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

-- Operational business records. Initial values are synthetic interview seeds.
-- Reruns preserve edited stock, rates, limits, settings and existing reports.

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
