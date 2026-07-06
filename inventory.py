"""Pure inventory and reporting logic for the Manuka stock app."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

import pandas as pd


RETAIL_PER_CARTON = 6
STOCK_LOCATIONS = ("Warehouse", "Chris Home", "Jang Home")


def format_carton_retail(quantity_retail: int, retail_per_carton: int = RETAIL_PER_CARTON) -> str:
    """Render a retail-box quantity as cartons plus loose retail boxes."""
    quantity_retail = int(quantity_retail)
    sign = "-" if quantity_retail < 0 else ""
    quantity_retail = abs(quantity_retail)
    cartons, retail = divmod(quantity_retail, retail_per_carton)
    parts: list[str] = []
    if cartons:
        parts.append(f"{cartons:,} carton{'s' if cartons != 1 else ''}")
    if retail or not parts:
        parts.append(f"{retail:,} retail")
    return sign + " + ".join(parts)


def location_balances(transactions: Iterable[dict]) -> dict[tuple[str, str], int]:
    """Calculate product/location balances exclusively from transaction effects."""
    balances: defaultdict[tuple[str, str], int] = defaultdict(int)
    for tx in transactions:
        product = tx["product"]
        quantity = int(tx["quantity_retail"])
        tx_type = tx["transaction_type"]
        from_location = tx.get("from_location")
        to_location = tx.get("to_location")

        if tx_type == "transfer":
            if from_location:
                balances[(product, from_location)] -= quantity
            if to_location:
                balances[(product, to_location)] += quantity
        elif tx_type in {"sale", "service"}:
            if from_location:
                balances[(product, from_location)] -= quantity
        elif tx_type in {"initial_stock", "return"}:
            if to_location:
                balances[(product, to_location)] += quantity
        elif tx_type == "adjustment":
            # Positive adjustments arrive at To; negative adjustments leave From.
            if quantity >= 0 and to_location:
                balances[(product, to_location)] += quantity
            elif quantity < 0 and from_location:
                balances[(product, from_location)] += quantity
    return dict(balances)


def dashboard_report(transactions: list[dict], products: list[dict]) -> pd.DataFrame:
    balances = location_balances(transactions)
    rows = []
    for product in products:
        name = product["name"]
        rpc = int(product.get("retail_per_carton", RETAIL_PER_CARTON))
        matching = [tx for tx in transactions if tx["product"] == name]
        initial = sum(int(tx["quantity_retail"]) for tx in matching if tx["transaction_type"] == "initial_stock")
        sold = sum(int(tx["quantity_retail"]) for tx in matching if tx["transaction_type"] == "sale")
        service = sum(int(tx["quantity_retail"]) for tx in matching if tx["transaction_type"] == "service")
        remaining = sum(balances.get((name, location), 0) for location in STOCK_LOCATIONS)
        rows.append(
            {
                "Product": name,
                "Initial stock": format_carton_retail(initial, rpc),
                "Sold quantity": format_carton_retail(sold, rpc),
                "Service quantity": format_carton_retail(service, rpc),
                "Warehouse stock": format_carton_retail(balances.get((name, "Warehouse"), 0), rpc),
                "Chris Home stock": format_carton_retail(balances.get((name, "Chris Home"), 0), rpc),
                "Jang Home stock": format_carton_retail(balances.get((name, "Jang Home"), 0), rpc),
                "Current remaining stock": format_carton_retail(remaining, rpc),
            }
        )
    return pd.DataFrame(rows)


def inventory_report(transactions: list[dict], products: list[dict]) -> pd.DataFrame:
    balances = location_balances(transactions)
    rows = []
    for product in products:
        rpc = int(product.get("retail_per_carton", RETAIL_PER_CARTON))
        for location in STOCK_LOCATIONS:
            retail = balances.get((product["name"], location), 0)
            rows.append(
                {
                    "Product": product["name"],
                    "Location": location,
                    "Retail quantity": retail,
                    "Carton format": format_carton_retail(retail, rpc),
                }
            )
    return pd.DataFrame(rows)


def sales_report(transactions: list[dict], products: list[dict]) -> pd.DataFrame:
    rows = []
    for product in products:
        sales = [tx for tx in transactions if tx["product"] == product["name"] and tx["transaction_type"] == "sale"]
        sold_retail = sum(int(tx["quantity_retail"]) for tx in sales)
        revenue = sum(Decimal(str(tx.get("total_amount") or 0)) for tx in sales)
        sold_cartons = Decimal(sold_retail) / Decimal(product.get("retail_per_carton", RETAIL_PER_CARTON))
        average = revenue / sold_cartons if sold_cartons else Decimal("0")
        rows.append(
            {
                "Product": product["name"],
                "Sold quantity (retail)": sold_retail,
                "Sold quantity": format_carton_retail(sold_retail, int(product.get("retail_per_carton", RETAIL_PER_CARTON))),
                "Average selling price / carton": float(average),
                "Sales revenue": float(revenue),
            }
        )
    return pd.DataFrame(rows)


def negative_balances_after(transactions: list[dict]) -> list[tuple[str, str, int]]:
    return [(product, location, qty) for (product, location), qty in location_balances(transactions).items() if qty < 0]
