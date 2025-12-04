"""
Test zobrazování tabulky "Přehled dat" v dashboardu.
Ověřuje správné formátování a zobrazení None hodnot pro growth metriky.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from dashboard.views import build_dashboard_context
from ingest.models import FinancialStatement, Document
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


def test_dashboard_table_display():
    """Test zobrazení tabulky s více lety a ověření None hodnot pro první rok."""

    # Vytvoření test usera
    test_user, _ = User.objects.get_or_create(
        username="test_dashboard_user",
        defaults={"email": "test@dashboard.com"}
    )

    # Vyčistit staré testy
    FinancialStatement.objects.filter(user=test_user).delete()
    Document.objects.filter(owner=test_user).delete()

    # Vytvořit data pro 3 roky
    years_data = [
        {
            "year": 2022,
            "income": {
                "revenue_products_services": 15000.0,
                "revenue_goods": 2000.0,
                "cogs_goods": 1500.0,
                "cogs_materials": 6000.0,
                "cogs_services": 1000.0,
                "personnel_costs": 3000.0,
                "depreciation": 400.0,
                "other_operating_expenses": 800.0,
                "taxes_fees": 150.0,
                "net_income": 3150.0,
            },
            "balance": {
                "receivables": 2500.0,
                "inventory": 1800.0,
                "trade_payables": 1200.0,
                "liabilities_short": 2000.0,
                "cash": 4000.0,
            },
        },
        {
            "year": 2023,
            "income": {
                "revenue_products_services": 18000.0,
                "revenue_goods": 2500.0,
                "cogs_goods": 1800.0,
                "cogs_materials": 8000.0,
                "cogs_services": 1200.0,
                "personnel_costs": 3500.0,
                "depreciation": 500.0,
                "other_operating_expenses": 1000.0,
                "taxes_fees": 200.0,
                "net_income": 3900.0,
            },
            "balance": {
                "receivables": 3000.0,
                "inventory": 2000.0,
                "trade_payables": 1500.0,
                "liabilities_short": 2500.0,
                "cash": 5000.0,
            },
        },
        {
            "year": 2024,
            "income": {
                "revenue_products_services": 21000.0,
                "revenue_goods": 3000.0,
                "cogs_goods": 2000.0,
                "cogs_materials": 9000.0,
                "cogs_services": 1400.0,
                "personnel_costs": 4000.0,
                "depreciation": 600.0,
                "other_operating_expenses": 1200.0,
                "taxes_fees": 250.0,
                "net_income": 4550.0,
            },
            "balance": {
                "receivables": 3500.0,
                "inventory": 2300.0,
                "trade_payables": 1800.0,
                "liabilities_short": 2800.0,
                "cash": 6000.0,
            },
        },
    ]

    # Vytvořit dokumenty a statements
    for data in years_data:
        doc = Document.objects.create(
            owner=test_user,
            year=data["year"],
            doc_type="income_statement",
            filename=f"test_{data['year']}.pdf",
            file=SimpleUploadedFile(f"test_{data['year']}.pdf", b"test content"),
        )
        FinancialStatement.objects.create(
            user=test_user,
            year=data["year"],
            document=doc,
            income=data["income"],
            balance=data["balance"],
        )

    print("=" * 80)
    print("TEST: Dashboard Table Display")
    print("=" * 80)

    # Získat context data
    context = build_dashboard_context(test_user)
    rows = context["table_rows"]

    print(f"\n[INFO] Found {len(rows)} years of data")

    # Ověřit strukturu dat
    errors = []

    for i, row in enumerate(rows):
        year = row["year"]
        print(f"\n[YEAR {year}]")
        print(f"  Revenue:       {row['revenue']:>10.2f}")
        print(f"  COGS:          {row['cogs']:>10.2f}")
        print(f"  Gross Margin:  {row['gross_margin']:>10.2f}")
        print(f"  Overheads:     {row['overheads']:>10.2f}")
        print(f"  EBIT:          {row['ebit']:>10.2f}")
        print(f"  Net Profit:    {row['net_profit']:>10.2f}")
        print(f"  GM%:           {row['profitability']['gm_pct']:>6.2f}%")
        print(f"  OP%:           {row['profitability']['op_pct']:>6.2f}%")
        print(f"  NP%:           {row['profitability']['np_pct']:>6.2f}%")

        # Growth values
        rev_growth = row['growth'].get('revenue')
        cogs_growth = row['growth'].get('cogs')
        overheads_growth = row['growth'].get('overheads')

        if i == 0:
            # První rok - growth by měl být None
            print(f"  Rev Growth:    None (očekáváno pro první rok)")
            print(f"  COGS Growth:   None (očekáváno pro první rok)")
            print(f"  OH Growth:     None (očekáváno pro první rok)")

            if rev_growth is not None:
                errors.append(f"Year {year}: Revenue growth should be None, got {rev_growth}")
            if cogs_growth is not None:
                errors.append(f"Year {year}: COGS growth should be None, got {cogs_growth}")
            if overheads_growth is not None:
                errors.append(f"Year {year}: Overheads growth should be None, got {overheads_growth}")
        else:
            # Další roky - growth by měl být číslo
            print(f"  Rev Growth:    {rev_growth:>6.2f}% (YoY)")
            print(f"  COGS Growth:   {cogs_growth:>6.2f}% (YoY)")
            print(f"  OH Growth:     {overheads_growth:>6.2f}% (YoY)")

            if rev_growth is None:
                errors.append(f"Year {year}: Revenue growth should not be None")
            if cogs_growth is None:
                errors.append(f"Year {year}: COGS growth should not be None")
            if overheads_growth is None:
                errors.append(f"Year {year}: Overheads growth should not be None")

    # Expected values pro rok 2023
    expected_2023 = {
        "revenue": 20500.0,  # 18000 + 2500
        "cogs": 9800.0,      # 1800 + 8000 (bez services!)
        "gross_margin": 10700.0,  # 20500 - 9800
        "overheads": 6400.0,  # 3500 + 500 + 1000 + 1200 + 200
        "ebit": 4300.0,      # 10700 - 6400
    }

    row_2023 = next((r for r in rows if r["year"] == 2023), None)
    if row_2023:
        print("\n[VERIFICATION] Year 2023:")
        for key, expected in expected_2023.items():
            actual = row_2023[key]
            status = "OK" if abs(actual - expected) < 0.01 else "FAIL"
            print(f"  {key:15s}: {actual:>10.2f} (expected: {expected:>10.2f}) {status}")
            if abs(actual - expected) > 0.01:
                errors.append(f"2023 {key}: expected {expected}, got {actual}")

    # Cleanup
    FinancialStatement.objects.filter(user=test_user).delete()
    Document.objects.filter(owner=test_user).delete()
    test_user.delete()

    if errors:
        print("\n[ERR] ERRORS DETECTED:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("\n" + "=" * 80)
        print("[OK] ALL DASHBOARD TABLE TESTS PASSED!")
        print("=" * 80)
        return True


if __name__ == "__main__":
    print("\nTESTING DASHBOARD TABLE DISPLAY\n")
    success = test_dashboard_table_display()
    sys.exit(0 if success else 1)
