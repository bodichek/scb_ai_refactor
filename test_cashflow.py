"""
Test cashflow výpočtů - ověřuje správnost Cash from Customers, Cash to Suppliers, atd.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from dashboard.cashflow import calculate_cashflow
from ingest.models import FinancialStatement, Document
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


def test_cashflow_calculations():
    """Test cashflow výpočtů s mock daty."""

    # Vytvoření test usera (pokud neexistuje)
    test_user, _ = User.objects.get_or_create(
        username="test_cashflow_user",
        defaults={"email": "test@cashflow.com"}
    )

    # Vyčistit staré testy
    FinancialStatement.objects.filter(user=test_user).delete()
    Document.objects.filter(owner=test_user).delete()

    # Vytvořit mock dokument pro 2023
    doc_2023 = Document.objects.create(
        owner=test_user,
        year=2023,
        doc_type="income_statement",
        filename="test_2023.pdf",
        file=SimpleUploadedFile("test_2023.pdf", b"test content"),
    )

    # Vytvořit mock data pro rok 2023
    fs_2023 = FinancialStatement.objects.create(
        user=test_user,
        year=2023,
        document=doc_2023,
        income={
            "revenue": 20000.0,
            "cogs": 10000.0,
            "cogs_services": 1500.0,
            "depreciation": 500.0,
            "net_income": 4000.0,
        },
        balance={
            "receivables": 3000.0,
            "inventory": 2000.0,
            "trade_payables": 1500.0,
            "liabilities_short": 2500.0,
            "cash": 5000.0,
        },
    )

    # Vytvořit mock dokument pro 2024
    doc_2024 = Document.objects.create(
        owner=test_user,
        year=2024,
        doc_type="income_statement",
        filename="test_2024.pdf",
        file=SimpleUploadedFile("test_2024.pdf", b"test content"),
    )

    # Vytvořit mock data pro rok 2024 (s změnami)
    FinancialStatement.objects.create(
        user=test_user,
        year=2024,
        document=doc_2024,
        income={
            "revenue": 24000.0,
            "cogs": 11000.0,
            "cogs_services": 1800.0,
            "depreciation": 600.0,
            "net_income": 5500.0,
        },
        balance={
            "receivables": 3500.0,  # +500
            "inventory": 2300.0,    # +300
            "trade_payables": 1800.0,  # +300
            "liabilities_short": 2800.0,  # +300
            "cash": 6000.0,
        },
    )

    print("=" * 80)
    print("TEST: Cashflow Calculations")
    print("=" * 80)

    # Vypočítat cashflow pro 2024
    cf = calculate_cashflow(test_user, 2024)

    if not cf:
        print("[ERR] Cashflow calculation returned None!")
        return False

    print("\n[BALANCE SHEET CHANGES - Delta]")
    print(f"  Delta Receivables:         {cf['delta_receivables']:>10.2f} (expected: 500.00)")
    print(f"  Delta Inventory:           {cf['delta_inventory']:>10.2f} (expected: 300.00)")
    print(f"  Delta Trade Payables:      {cf['delta_payables']:>10.2f} (expected: 300.00)")
    print(f"  Delta ST Liabilities:      {cf['delta_short_term_liabilities']:>10.2f} (expected: 300.00)")

    print("\n[WORKING CAPITAL]")
    # Delta WC = Delta(Zasoby) + Delta(Pohledavky) - Delta(Kratkodobe zavazky)
    # Delta WC = 300 + 500 - 300 = 500
    expected_wc_change = 500.0
    print(f"  Working Capital Change:    {cf['working_capital_change']:>10.2f} (expected: {expected_wc_change:.2f})")

    print("\n[DIRECT METHOD]")
    # Cash from Customers = Revenue - Delta(Pohledavky)
    # = 24000 - 500 = 23500
    expected_cash_from_customers = 23500.0
    print(f"  Cash from Customers:       {cf['cash_from_customers']:>10.2f} (expected: {expected_cash_from_customers:.2f})")

    # Cash to Suppliers = (COGS + services) + Delta(Zasoby) - Delta(Zavazky)
    # = (11000 + 1800) + 300 - 300 = 12800
    expected_cash_to_suppliers = 12800.0
    print(f"  Cash to Suppliers:         {cf['cash_to_suppliers']:>10.2f} (expected: {expected_cash_to_suppliers:.2f})")

    # Gross Cash Profit = Cash from Customers - Cash to Suppliers
    # = 23500 - 12800 = 10700
    expected_gross_cash_profit = 10700.0
    print(f"  Gross Cash Profit:         {cf['gross_cash_profit']:>10.2f} (expected: {expected_gross_cash_profit:.2f})")

    print("\n[INDIRECT METHOD]")
    # OCF = Net Profit + Depreciation - Delta(Working Capital)
    # = 5500 + 600 - 500 = 5600
    expected_ocf = 5600.0
    print(f"  Operating Cash Flow:       {cf['operating_cf']:>10.2f} (expected: {expected_ocf:.2f})")

    # Verification
    errors = []

    if abs(cf['delta_receivables'] - 500.0) > 0.01:
        errors.append(f"Δ Receivables: expected 500.0, got {cf['delta_receivables']}")
    if abs(cf['delta_inventory'] - 300.0) > 0.01:
        errors.append(f"Δ Inventory: expected 300.0, got {cf['delta_inventory']}")
    if abs(cf['delta_payables'] - 300.0) > 0.01:
        errors.append(f"Δ Payables: expected 300.0, got {cf['delta_payables']}")
    if abs(cf['working_capital_change'] - expected_wc_change) > 0.01:
        errors.append(f"WC Change: expected {expected_wc_change}, got {cf['working_capital_change']}")
    if abs(cf['cash_from_customers'] - expected_cash_from_customers) > 0.01:
        errors.append(f"Cash from Customers: expected {expected_cash_from_customers}, got {cf['cash_from_customers']}")
    if abs(cf['cash_to_suppliers'] - expected_cash_to_suppliers) > 0.01:
        errors.append(f"Cash to Suppliers: expected {expected_cash_to_suppliers}, got {cf['cash_to_suppliers']}")
    if abs(cf['gross_cash_profit'] - expected_gross_cash_profit) > 0.01:
        errors.append(f"Gross Cash Profit: expected {expected_gross_cash_profit}, got {cf['gross_cash_profit']}")
    if abs(cf['operating_cf'] - expected_ocf) > 0.01:
        errors.append(f"Operating CF: expected {expected_ocf}, got {cf['operating_cf']}")

    # Cleanup
    FinancialStatement.objects.filter(user=test_user).delete()
    test_user.delete()

    if errors:
        print("\n[ERR] ERRORS DETECTED:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("\n" + "=" * 80)
        print("[OK] ALL CASHFLOW TESTS PASSED!")
        print("=" * 80)
        return True


if __name__ == "__main__":
    print("\nTESTING CASHFLOW CALCULATIONS\n")
    success = test_cashflow_calculations()
    sys.exit(0 if success else 1)
