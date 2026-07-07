insert into products (sku, name, retail_per_carton) values
  ('MGO100', 'MGO 100+', 6), ('MGO300', 'MGO 300+', 6)
on conflict (sku) do update set name = excluded.name, retail_per_carton = excluded.retail_per_carton;

insert into locations (name) values
  ('Australia'), ('Warehouse'), ('Chris Home'), ('Brian Home'), ('Customer'), ('Service')
on conflict (name) do nothing;

-- Idempotent historical seed: only insert when the transaction table is empty.
insert into transactions (transaction_date, product_id, transaction_type, quantity, unit, quantity_retail, from_location_id, to_location_id, unit_price, total_amount, memo)
select date '2026-07-05', p.id, v.transaction_type, v.quantity, v.unit, v.quantity_retail, fl.id, tl.id, v.unit_price, v.total_amount, v.memo
from (values
 ('MGO100','initial_stock',444::numeric,'carton',2664,'Australia','Warehouse',null::numeric,null::numeric,'Initial stock received from Australia'),
 ('MGO300','initial_stock',444,'carton',2664,'Australia','Warehouse',null,null,'Initial stock received from Australia'),
 ('MGO300','transfer',70,'carton',420,'Warehouse','Chris Home',null,null,'Moved stock to Chris Home for sales'),
 ('MGO100','transfer',30,'carton',180,'Warehouse','Chris Home',null,null,'Moved stock to Chris Home for sales'),
 ('MGO300','sale',45,'carton',270,'Chris Home','Customer',89,4005,'Sold MGO 300+ cartons'),
 ('MGO100','sale',15,'carton',90,'Chris Home','Customer',69,1035,'Sold MGO 100+ cartons'),
 ('MGO300','service',2,'retail',2,'Chris Home','Service',null,0,'Service / giveaway'),
 ('MGO100','service',3,'retail',3,'Chris Home','Service',null,0,'Service / giveaway'),
 ('MGO300','transfer',8,'carton',48,'Chris Home','Brian Home',null,null,'Moved stock to Brian Home'),
 ('MGO100','transfer',6,'carton',36,'Chris Home','Brian Home',null,null,'Moved stock to Brian Home')
) as v(sku,transaction_type,quantity,unit,quantity_retail,from_name,to_name,unit_price,total_amount,memo)
join products p on p.sku = v.sku
left join locations fl on fl.name = v.from_name
left join locations tl on tl.name = v.to_name
where not exists (select 1 from transactions);
