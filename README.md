# Manuka Honey Sticks Inventory

An internal Streamlit app that calculates product-level inventory from an immutable transaction log. MGO 100+ and MGO 300+ stock are always reported separately; revenue can be combined.

## Run locally

1. Create and activate a Python virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your credentials.
4. Run: `streamlit run app.py`

If Supabase credentials are absent, the app starts in demo mode with the supplied historical transactions. The default demo password is `manuka-demo`; set `APP_PASSWORD` before deployment.

## Supabase setup

1. Create a Supabase project.
2. Run `sql/schema.sql` in the Supabase SQL editor.
3. Run `sql/seed.sql` once. It is safe to rerun; historical transactions are inserted only when the table is empty.
4. Set `SUPABASE_URL`, `SUPABASE_KEY`, and `APP_PASSWORD` in Streamlit secrets or environment variables.

Use a server-side Supabase key because row-level security is enabled and the key stays on the Streamlit server. Never commit `.streamlit/secrets.toml` or expose a privileged key in client-side code.

## Reports and exports

- Dashboard: stock movement summary by product
- Inventory by Location: Warehouse, Chris Home, and Jang Home balances
- Sales Report: per-product quantity, average carton price, and combined revenue
- Transaction Log: date/product/type/location filters
- CSV downloads are available on inventory, sales, and log pages

## Validation

Run `pytest -q`. Tests verify the expected 2,571 and 2,392 retail balances and combined $5,040 sales revenue.

## Deployment

Deploy the repository to Streamlit Community Cloud or another Python host, set the three secrets in the host dashboard, and use `app.py` as the entry point.
