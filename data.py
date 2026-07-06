"""Supabase repository and deterministic demo data."""

from __future__ import annotations

import os
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import streamlit as st


PRODUCTS = [
    {"id": "11111111-1111-1111-1111-111111111111", "sku": "MGO100", "name": "MGO 100+", "retail_per_carton": 6},
    {"id": "22222222-2222-2222-2222-222222222222", "sku": "MGO300", "name": "MGO 300+", "retail_per_carton": 6},
]
LOCATIONS = [
    {"id": f"00000000-0000-0000-0000-00000000000{i}", "name": name}
    for i, name in enumerate(["Australia", "Warehouse", "Chris Home", "Jang Home", "Customer", "Service"], start=1)
]


def _tx(product: str, kind: str, quantity: float, unit: str, retail: int, source: str, destination: str, price: float | None, memo: str, tx_id: int) -> dict:
    return {
        "id": str(tx_id), "transaction_date": "2026-07-05", "product": product,
        "transaction_type": kind, "quantity": quantity, "unit": unit,
        "quantity_retail": retail, "from_location": source, "to_location": destination,
        "unit_price": price, "total_amount": quantity * price if price is not None else (0 if kind == "service" else None),
        "memo": memo, "created_at": f"2026-07-05T12:{tx_id:02d}:00+00:00",
    }


SEED_TRANSACTIONS = [
    _tx("MGO 100+", "initial_stock", 444, "carton", 2664, "Australia", "Warehouse", None, "Initial stock received from Australia", 1),
    _tx("MGO 300+", "initial_stock", 444, "carton", 2664, "Australia", "Warehouse", None, "Initial stock received from Australia", 2),
    _tx("MGO 300+", "transfer", 70, "carton", 420, "Warehouse", "Chris Home", None, "Moved stock to Chris Home for sales", 3),
    _tx("MGO 100+", "transfer", 30, "carton", 180, "Warehouse", "Chris Home", None, "Moved stock to Chris Home for sales", 4),
    _tx("MGO 300+", "sale", 45, "carton", 270, "Chris Home", "Customer", 89, "Sold MGO 300+ cartons", 5),
    _tx("MGO 100+", "sale", 15, "carton", 90, "Chris Home", "Customer", 69, "Sold MGO 100+ cartons", 6),
    _tx("MGO 300+", "service", 2, "retail", 2, "Chris Home", "Service", None, "Service / giveaway", 7),
    _tx("MGO 100+", "service", 3, "retail", 3, "Chris Home", "Service", None, "Service / giveaway", 8),
    _tx("MGO 300+", "transfer", 8, "carton", 48, "Chris Home", "Jang Home", None, "Moved stock to Jang Home", 9),
    _tx("MGO 100+", "transfer", 6, "carton", 36, "Chris Home", "Jang Home", None, "Moved stock to Jang Home", 10),
]


def _secret(name: str, default: Any = None) -> Any:
    env_value = os.getenv(name)
    if env_value is not None:
        return env_value
    secret_files = (Path.cwd() / ".streamlit" / "secrets.toml", Path.home() / ".streamlit" / "secrets.toml")
    if any(path.exists() for path in secret_files):
        return st.secrets.get(name, default)
    return default


class Repository:
    def __init__(self) -> None:
        self.url = _secret("SUPABASE_URL")
        self.key = _secret("SUPABASE_KEY")
        self.demo = not (self.url and self.key)
        self.client = None
        if not self.demo:
            from supabase import create_client
            self.client = create_client(self.url, self.key)

    def products(self) -> list[dict]:
        if self.demo:
            return deepcopy(PRODUCTS)
        return self.client.table("products").select("*").order("name").execute().data

    def locations(self) -> list[dict]:
        if self.demo:
            return deepcopy(LOCATIONS)
        return self.client.table("locations").select("*").order("name").execute().data

    def transactions(self) -> list[dict]:
        if self.demo:
            if "demo_transactions" not in st.session_state:
                st.session_state.demo_transactions = deepcopy(SEED_TRANSACTIONS)
            return deepcopy(st.session_state.demo_transactions)

        rows = self.client.table("transactions").select(
            "id,transaction_date,transaction_type,quantity,unit,quantity_retail,unit_price,total_amount,memo,created_at,"
            "product:products!transactions_product_id_fkey(name),"
            "from_loc:locations!transactions_from_location_id_fkey(name),"
            "to_loc:locations!transactions_to_location_id_fkey(name)"
        ).order("transaction_date", desc=True).order("created_at", desc=True).execute().data
        return [
            {
                **{k: v for k, v in row.items() if k not in {"product", "from_loc", "to_loc"}},
                "product": row["product"]["name"],
                "from_location": row["from_loc"]["name"] if row.get("from_loc") else None,
                "to_location": row["to_loc"]["name"] if row.get("to_loc") else None,
            }
            for row in rows
        ]

    def add_transaction(self, tx: dict) -> None:
        if self.demo:
            tx = {**tx, "id": str(len(st.session_state.demo_transactions) + 1), "created_at": date.today().isoformat()}
            st.session_state.demo_transactions.insert(0, tx)
            return
        products = {p["name"]: p["id"] for p in self.products()}
        locations = {loc["name"]: loc["id"] for loc in self.locations()}
        payload = {
            "transaction_date": str(tx["transaction_date"]), "product_id": products[tx["product"]],
            "transaction_type": tx["transaction_type"], "quantity": tx["quantity"], "unit": tx["unit"],
            "quantity_retail": tx["quantity_retail"],
            "from_location_id": locations.get(tx.get("from_location")), "to_location_id": locations.get(tx.get("to_location")),
            "unit_price": tx.get("unit_price"), "total_amount": tx.get("total_amount"), "memo": tx.get("memo"),
        }
        self.client.table("transactions").insert(payload).execute()
