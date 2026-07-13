from datetime import date

from data import PRODUCTS, SEED_TRANSACTIONS
from inventory import dashboard_report, format_carton_retail, inventory_report, sales_report


def test_format_carton_retail():
    assert format_carton_retail(36) == "6 cartons"
    assert format_carton_retail(51) == "8 cartons + 3 retail"
    assert format_carton_retail(3) == "3 retail"


def test_expected_inventory_results():
    report = inventory_report(SEED_TRANSACTIONS, PRODUCTS).set_index(["Product", "Location"])
    assert report.loc[("MGO 100+", "Warehouse"), "Retail quantity"] == 2478
    assert report.loc[("MGO 100+", "Chris Home"), "Retail quantity"] == 57
    assert report.loc[("MGO 100+", "Brian Home"), "Retail quantity"] == 36
    assert report.loc[("MGO 300+", "Warehouse"), "Retail quantity"] == 2238
    assert report.loc[("MGO 300+", "Chris Home"), "Retail quantity"] == 106
    assert report.loc[("MGO 300+", "Brian Home"), "Retail quantity"] == 48


def test_expected_dashboard_and_sales():
    dashboard = dashboard_report(SEED_TRANSACTIONS, PRODUCTS).set_index("Product")
    assert dashboard.loc["MGO 100+", "Current remaining stock"] == "428 cartons + 3 retail"
    assert dashboard.loc["MGO 300+", "Current remaining stock"] == "398 cartons + 4 retail"
    sales = sales_report(SEED_TRANSACTIONS, PRODUCTS).set_index(["Date", "Product"])
    report_date = date(2026, 7, 5)
    assert sales.loc[(report_date, "MGO 100+"), "Sales revenue"] == 1035
    assert sales.loc[(report_date, "MGO 300+"), "Sales revenue"] == 4005
    assert sales.loc[(report_date, "MGO 100+"), "Sold quantity"] == "15 cartons"
    assert "Date" in sales_report(SEED_TRANSACTIONS, PRODUCTS).columns
    assert sales["Sales revenue"].sum() == 5040
