from __future__ import annotations

import hmac
import importlib
import os
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

import inventory as inventory_module
from data import Repository

inventory_module = importlib.reload(inventory_module)
from inventory import (
    STOCK_LOCATIONS,
    dashboard_report,
    format_carton_retail,
    inventory_report,
    negative_balances_after,
    sales_report,
)


st.set_page_config(page_title="Manuka Inventory", page_icon="🍯", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  :root { --honey:#D99A18; --ink:#2A2419; --cream:#FFF9EB; }
  .stApp { background: linear-gradient(145deg, #fffdf8 0%, #fff8e8 100%); }
  [data-testid="stSidebar"] { background:#29251e; }
  [data-testid="stSidebar"] * { color:#fff8e8; }
  [data-testid="stSidebar"] .stButton button, [data-testid="stSidebar"] .stButton button * { color:#2A2419; }
  h1,h2,h3 { color:var(--ink); letter-spacing:-.02em; }
  [data-testid="stMetric"] { background:white; border:1px solid #eedeb8; border-radius:14px; padding:16px; box-shadow:0 4px 18px #5f471214; }
  [data-testid="stMetricValue"] { font-size:1.45rem; }
  .eyebrow { color:#9b6700; font-weight:700; text-transform:uppercase; letter-spacing:.12em; font-size:.76rem; }
  .mode-pill { display:inline-block; padding:4px 10px; border-radius:999px; background:#fff0c7; color:#765000; font-size:.8rem; }
  div[data-testid="stDataFrame"] { border:1px solid #ead9b2; border-radius:12px; overflow:hidden; }
  .stButton>button, .stDownloadButton>button { border-radius:10px; font-weight:700; }
</style>
""", unsafe_allow_html=True)


def secret(name: str, default=None):
    env_value = os.getenv(name)
    if env_value is not None:
        return env_value
    secret_files = (Path.cwd() / ".streamlit" / "secrets.toml", Path.home() / ".streamlit" / "secrets.toml")
    if any(path.exists() for path in secret_files):
        return st.secrets.get(name, default)
    return default


def require_password() -> bool:
    expected = secret("APP_PASSWORD", "manuka-demo")
    if st.session_state.get("authenticated"):
        return True
    left, center, right = st.columns([1, 1.3, 1])
    with center:
        st.markdown("<div class='eyebrow'>Internal operations</div>", unsafe_allow_html=True)
        st.title("🍯 Manuka Inventory")
        st.caption("Enter the team password to continue.")
        with st.form("login"):
            entered = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Open inventory", use_container_width=True)
        if submitted:
            if hmac.compare_digest(entered, str(expected)):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("That password doesn’t match.")
        if expected == "manuka-demo":
            st.info("Demo password: **manuka-demo**")
    return False


if not require_password():
    st.stop()

repo = Repository()
products = repo.products()
locations = repo.locations()
transactions = repo.transactions()

with st.sidebar:
    st.markdown("## 🍯 Manuka Sticks")
    st.caption("Inventory operations")
    page = st.radio("Navigation", ["Dashboard", "Transaction Entry", "Inventory by Location", "Sales Report", "Transaction Log"], label_visibility="collapsed")
    st.divider()
    st.markdown(f"<span class='mode-pill'>{'Demo data' if repo.demo else 'Supabase connected'}</span>", unsafe_allow_html=True)
    st.caption("1 carton = 6 retail boxes")
    if st.button("Sign out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()


def heading(title: str, subtitle: str) -> None:
    st.markdown("<div class='eyebrow'>Manuka Honey Sticks</div>", unsafe_allow_html=True)
    st.title(title)
    st.caption(subtitle)


def csv_button(df: pd.DataFrame, label: str, filename: str) -> None:
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), filename, "text/csv", use_container_width=True)


if page == "Dashboard":
    heading("Inventory dashboard", "A live picture calculated from every stock movement.")
    report = dashboard_report(transactions, products)
    sales = sales_report(transactions, products)
    c1, c2, c3 = st.columns(3)
    for column, product in zip((c1, c2), products):
        remaining = report.loc[report["Product"] == product["name"], "Current remaining stock"].iloc[0]
        column.metric(product["name"], remaining, "Current stock")
    c3.metric("Combined revenue", f"${sales['Sales revenue'].sum():,.2f}", "All products")
    st.subheader("Stock position")
    st.dataframe(report, hide_index=True, use_container_width=True)
    warnings = negative_balances_after(transactions)
    if warnings:
        for product, location, qty in warnings:
            st.warning(f"Negative stock: {product} at {location} is {format_carton_retail(qty)}.")

elif page == "Transaction Entry":
    heading("Add a transaction", "Every change is recorded; inventory balances are never edited directly.")
    product_map = {p["name"]: p for p in products}
    location_names = [loc["name"] for loc in locations]
    with st.form("transaction", clear_on_submit=True):
        a, b, c = st.columns(3)
        tx_date = a.date_input("Date", value=date.today())
        product_name = b.selectbox("Product", list(product_map))
        tx_type = c.selectbox("Transaction type", ["initial_stock", "transfer", "sale", "service", "adjustment", "return"])
        d, e, f = st.columns(3)
        quantity = d.number_input("Quantity", min_value=-100000.0 if tx_type == "adjustment" else 0.0, step=1.0)
        unit = e.selectbox("Unit", ["carton", "retail"])
        unit_price = f.number_input("Unit price ($)", min_value=0.0, step=1.0, help="Price per selected unit")
        g, h = st.columns(2)
        from_location = g.selectbox("From location", ["—"] + location_names, index=location_names.index("Australia") + 1 if tx_type == "initial_stock" else 0)
        to_location = h.selectbox("To location", ["—"] + location_names, index=location_names.index("Warehouse") + 1 if tx_type == "initial_stock" else 0)
        memo = st.text_area("Memo", placeholder="What happened? Add useful context for the team.")
        submitted = st.form_submit_button("Record transaction", use_container_width=True)

    if submitted:
        errors = []
        if quantity == 0:
            errors.append("Quantity cannot be zero.")
        if tx_type == "sale" and unit_price <= 0:
            errors.append("Sale transactions require a unit price.")
        if tx_type == "service" and unit_price != 0:
            errors.append("Service transactions must have a zero or blank unit price.")
        if tx_type == "adjustment" and not memo.strip():
            errors.append("Adjustments require a memo.")
        if tx_type in {"transfer", "sale", "service"} and from_location == "—":
            errors.append(f"{tx_type.replace('_', ' ').title()} requires a From location.")
        if tx_type in {"initial_stock", "transfer", "return"} and to_location == "—":
            errors.append(f"{tx_type.replace('_', ' ').title()} requires a To location.")
        if tx_type == "adjustment" and ((quantity > 0 and to_location == "—") or (quantity < 0 and from_location == "—")):
            errors.append("Positive adjustments need a To location; negative adjustments need a From location.")
        if errors:
            for error in errors:
                st.error(error)
        else:
            rpc = int(product_map[product_name]["retail_per_carton"])
            quantity_retail = int(quantity * rpc if unit == "carton" else quantity)
            total = quantity * unit_price if tx_type == "sale" else (-quantity * unit_price if tx_type == "return" and unit_price else (0 if tx_type == "service" else None))
            tx = {"transaction_date": tx_date, "product": product_name, "transaction_type": tx_type, "quantity": quantity,
                  "unit": unit, "quantity_retail": quantity_retail, "from_location": None if from_location == "—" else from_location,
                  "to_location": None if to_location == "—" else to_location, "unit_price": unit_price or None,
                  "total_amount": total, "memo": memo.strip() or None}
            repo.add_transaction(tx)
            updated = repo.transactions()
            negatives = negative_balances_after(updated)
            st.success(f"Recorded {tx_type.replace('_', ' ')}: {format_carton_retail(quantity_retail, rpc)} of {product_name}.")
            if negatives:
                st.warning("This transaction leaves one or more locations with negative stock. Review the dashboard.")

elif page == "Inventory by Location":
    heading("Inventory by location", "Physical stock remains separated by product and location.")
    report = inventory_report(transactions, products)
    st.dataframe(report, hide_index=True, use_container_width=True)
    csv_button(report, "Download inventory CSV", "inventory_by_location.csv")

elif page == "Sales Report":
    heading("Sales report", "Daily sales volume, carton pricing, and revenue by product.")
    report = sales_report(transactions, products)
    if report.empty:
        st.info("No sales transactions yet.")
    else:
        report["Date"] = pd.to_datetime(report["Date"]).dt.date
        min_date, max_date = report["Date"].min(), report["Date"].max()
        date_range = st.date_input("Sales date range", (min_date, max_date))
        filtered = report.copy()
        if len(date_range) == 2:
            filtered = filtered[(filtered["Date"] >= date_range[0]) & (filtered["Date"] <= date_range[1])]

        st.metric("Total combined sales revenue", f"${filtered['Sales revenue'].sum():,.2f}")
        display = filtered.drop(columns=["Sold quantity (retail)"]).copy()
        st.dataframe(display, hide_index=True, use_container_width=True, column_config={
            "Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "Average selling price / carton": st.column_config.NumberColumn(format="$%.2f"),
            "Sales revenue": st.column_config.NumberColumn(format="$%.2f"),
        })
        csv_button(filtered, "Download sales report CSV", "sales_report.csv")

elif page == "Transaction Log":
    heading("Transaction log", "The complete audit trail for stock and sales.")
    df = pd.DataFrame(transactions)
    if not df.empty:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.date
        min_date, max_date = df["transaction_date"].min(), df["transaction_date"].max()
        c1, c2, c3, c4 = st.columns(4)
        date_range = c1.date_input("Date range", (min_date, max_date))
        product_filter = c2.multiselect("Product", sorted(df["product"].dropna().unique()))
        type_filter = c3.multiselect("Type", sorted(df["transaction_type"].dropna().unique()))
        all_locations = sorted(set(df["from_location"].dropna()) | set(df["to_location"].dropna()))
        location_filter = c4.multiselect("Location", all_locations)
        filtered = df.copy()
        if len(date_range) == 2:
            filtered = filtered[(filtered["transaction_date"] >= date_range[0]) & (filtered["transaction_date"] <= date_range[1])]
        if product_filter:
            filtered = filtered[filtered["product"].isin(product_filter)]
        if type_filter:
            filtered = filtered[filtered["transaction_type"].isin(type_filter)]
        if location_filter:
            filtered = filtered[filtered["from_location"].isin(location_filter) | filtered["to_location"].isin(location_filter)]
        columns = ["transaction_date", "product", "transaction_type", "quantity", "unit", "quantity_retail", "from_location", "to_location", "unit_price", "total_amount", "memo"]
        st.dataframe(filtered[columns], hide_index=True, use_container_width=True)
        csv_button(filtered[columns], "Download transaction log CSV", "transaction_log.csv")
    else:
        st.info("No transactions yet.")
