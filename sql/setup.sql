create extension if not exists pgcrypto;

create table if not exists products (
  id uuid primary key default gen_random_uuid(),
  sku text not null unique,
  name text not null unique,
  retail_per_carton integer not null default 6 check (retail_per_carton > 0)
);

create table if not exists locations (
  id uuid primary key default gen_random_uuid(),
  name text not null unique
);

create table if not exists transactions (
  id uuid primary key default gen_random_uuid(),
  transaction_date date not null,
  product_id uuid not null references products(id),
  transaction_type text not null check (transaction_type in ('initial_stock','transfer','sale','service','adjustment','return')),
  quantity numeric not null check (quantity <> 0),
  unit text not null check (unit in ('carton','retail')),
  quantity_retail integer not null,
  from_location_id uuid references locations(id),
  to_location_id uuid references locations(id),
  unit_price numeric(12,2),
  total_amount numeric(14,2),
  memo text,
  created_at timestamptz not null default now(),
  constraint sale_requires_price check (transaction_type <> 'sale' or unit_price > 0),
  constraint service_is_free check (transaction_type <> 'service' or coalesce(unit_price, 0) = 0),
  constraint adjustment_requires_memo check (transaction_type <> 'adjustment' or length(trim(coalesce(memo,''))) > 0)
);

create index if not exists transactions_date_idx on transactions(transaction_date desc);
create index if not exists transactions_product_idx on transactions(product_id);
create index if not exists transactions_from_idx on transactions(from_location_id);
create index if not exists transactions_to_idx on transactions(to_location_id);

alter table products enable row level security;
alter table locations enable row level security;
alter table transactions enable row level security;

grant usage on schema public to service_role;
grant all privileges on all tables in schema public to service_role;
grant all privileges on all sequences in schema public to service_role;
alter default privileges in schema public grant all on tables to service_role;
alter default privileges in schema public grant all on sequences to service_role;

insert into products (sku, name, retail_per_carton) values
  ('MGO100', 'MGO 100+', 6), ('MGO300', 'MGO 300+', 6)
on conflict (sku) do update set name = excluded.name, retail_per_carton = excluded.retail_per_carton;

insert into locations (name) values
  ('Australia'), ('Warehouse'), ('Chris Home'), ('Brian Home'), ('Customer'), ('Service')
on conflict (name) do nothing;

insert into transactions (transaction_date, product_id, transaction_type, quantity, unit, quantity_retail, from_location_id, to_location_id, unit_price, total_amount, memo)
select v.transaction_date, p.id, v.transaction_type, v.quantity, v.unit, v.quantity_retail, fl.id, tl.id, v.unit_price, v.total_amount, v.memo
from (values
 ('2026-07-05'::date,'MGO100','initial_stock',444::numeric,'carton',2664,'Australia','Warehouse',null::numeric,null::numeric,'Initial stock received from Australia'),
 ('2026-07-05'::date,'MGO300','initial_stock',444,'carton',2664,'Australia','Warehouse',null,null,'Initial stock received from Australia'),
 ('2026-07-05'::date,'MGO300','transfer',70,'carton',420,'Warehouse','Chris Home',null,null,'Moved stock to Chris Home for sales'),
 ('2026-07-05'::date,'MGO100','transfer',30,'carton',180,'Warehouse','Chris Home',null,null,'Moved stock to Chris Home for sales'),
 ('2026-07-05'::date,'MGO300','sale',45,'carton',270,'Chris Home','Customer',89,4005,'Sold MGO 300+ cartons'),
 ('2026-07-05'::date,'MGO100','sale',15,'carton',90,'Chris Home','Customer',69,1035,'Sold MGO 100+ cartons'),
 ('2026-07-05'::date,'MGO300','service',2,'retail',2,'Chris Home','Service',null,0,'Service / giveaway'),
 ('2026-07-05'::date,'MGO100','service',3,'retail',3,'Chris Home','Service',null,0,'Service / giveaway'),
 ('2026-07-05'::date,'MGO300','transfer',8,'carton',48,'Chris Home','Brian Home',null,null,'Moved stock to Brian Home'),
 ('2026-07-05'::date,'MGO100','transfer',6,'carton',36,'Chris Home','Brian Home',null,null,'Moved stock to Brian Home'),
 ('2026-07-01'::date,'MGO100','transfer',1,'carton',6,'Warehouse','Chris Home',null,null,'Moved 1 carton from Vancouver Warehouse to Chris Home on 2026-07-01'),
 ('2026-07-01'::date,'MGO300','transfer',1,'carton',6,'Warehouse','Chris Home',null,null,'Moved 1 carton from Vancouver Warehouse to Chris Home on 2026-07-01')
) as v(transaction_date,sku,transaction_type,quantity,unit,quantity_retail,from_name,to_name,unit_price,total_amount,memo)
join products p on p.sku = v.sku
left join locations fl on fl.name = v.from_name
left join locations tl on tl.name = v.to_name
where not exists (select 1 from transactions);
