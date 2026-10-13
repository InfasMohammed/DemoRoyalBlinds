-- Generated from backend/app/data/company_knowledge.json.
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
commit;

-- Populated source text is searchable locally immediately. Vector embeddings
-- remain NULL until backend/scripts/index_knowledge.py succeeds with credentials.
select category, count(*) as passages, count(embedding) as embedded_passages
from public.company_knowledge_chunks group by category order by category;
