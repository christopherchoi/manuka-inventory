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

-- The Streamlit server should use a server-side Supabase key. Do not expose it in a browser.
alter table products enable row level security;
alter table locations enable row level security;
alter table transactions enable row level security;

-- New Supabase projects can disable automatic API grants. Grant only the
-- server-side service role; anon/authenticated remain unable to access data.
grant usage on schema public to service_role;
grant all privileges on all tables in schema public to service_role;
grant all privileges on all sequences in schema public to service_role;
alter default privileges in schema public grant all on tables to service_role;
alter default privileges in schema public grant all on sequences to service_role;
