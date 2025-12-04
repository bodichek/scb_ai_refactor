"""
Test správnosti dat pro grafy v dashboardu.
Ověřuje, že compute_metrics() správně počítá hodnoty z vision parser formátu.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from finance.utils import compute_metrics


def test_vision_parser_format():
    """Test výpočtů s daty z vision parseru."""

    # Simulovaný FinancialStatement s vision parser daty
    class MockFS:
        def __init__(self):
            self.income = {
                # Revenue components
                "revenue_products_services": 18000.0,  # v tisících Kč
                "revenue_goods": 2500.0,

                # COGS components
                "cogs_goods": 1800.0,
                "cogs_materials": 8000.0,
                "cogs_services": 1200.0,

                # Overhead components
                "personnel_costs": 3500.0,           # Agregát
                "personnel_costs_wages": 2800.0,     # Detail (neměl by se počítat)
                "personnel_costs_social": 700.0,     # Detail (neměl by se počítat)
                "depreciation": 500.0,
                "other_operating_expenses": 1000.0,

                # Other
                "interest_expense": 200.0,
                "tax": 400.0,
                "net_income": 3900.0,
            }
            self.balance = {
                "assets_total": 50000.0,
                "equity": 20000.0,
                "liabilities": 30000.0,
            }

    fs = MockFS()
    metrics = compute_metrics(fs)

    print("=" * 80)
    print("TEST: Vision Parser Format")
    print("=" * 80)

    # Expected values
    expected = {
        "revenue": 20500.0,        # 18000 + 2500
        "cogs": 11000.0,           # 1800 + 8000 + 1200
        "gross_margin": 9500.0,    # 20500 - 11000
        "overheads": 5000.0,       # 3500 (personnel) + 500 (depreciation) + 1000 (other)
        "ebit": 4500.0,            # 9500 - 5000
        "net_profit": 3900.0,      # net_income from vision parser (after tax, interest)
    }

    print("\n[METRICS] CALCULATED METRICS:")
    print(f"Revenue:       {metrics['revenue']:>10.2f} (expected: {expected['revenue']:.2f})")
    print(f"COGS:          {metrics['cogs']:>10.2f} (expected: {expected['cogs']:.2f})")
    print(f"Gross Margin:  {metrics['gross_margin']:>10.2f} (expected: {expected['gross_margin']:.2f})")
    print(f"Overheads:     {metrics['overheads']:>10.2f} (expected: {expected['overheads']:.2f})")
    print(f"EBIT:          {metrics['ebit']:>10.2f} (expected: {expected['ebit']:.2f})")
    print(f"Net Profit:    {metrics['net_profit']:>10.2f} (expected: {expected['net_profit']:.2f})")

    print("\n[METRICS] PROFITABILITY MARGINS:")
    print(f"Gross Margin %:    {metrics['profitability']['gm_pct']:>6.2f}%")
    print(f"Operating Margin %: {metrics['profitability']['op_pct']:>6.2f}%")
    print(f"Net Margin %:       {metrics['profitability']['np_pct']:>6.2f}%")

    # Verify
    errors = []
    for key, expected_value in expected.items():
        actual = metrics[key]
        if abs(actual - expected_value) > 0.01:
            errors.append(f"[ERR] {key}: expected {expected_value}, got {actual}")

    if errors:
        print("\n[ERR] ERRORS:")
        for err in errors:
            print(f"  {err}")
        return False
    else:
        print("\n[OK] ALL TESTS PASSED!")
        return True


def test_legacy_format():
    """Test výpočtů s legacy daty (starý parser)."""

    class MockFS:
        def __init__(self):
            self.income = {
                "Revenue": 15000.0,
                "COGS": 9000.0,
                "Services": 1500.0,  # Should be subtracted from COGS
                "PersonnelWages": 2000.0,
                "PersonnelInsurance": 500.0,
                "Depreciation": 300.0,
                "OtherOperatingCosts": 800.0,
            }
            self.balance = {}

    fs = MockFS()
    metrics = compute_metrics(fs)

    print("\n" + "=" * 80)
    print("TEST: Legacy Parser Format")
    print("=" * 80)

    # Expected: COGS should be 9000 - 1500 (services) = 7500
    # Overheads: 1500 (services) + 2000 + 500 + 300 + 800 = 5100
    expected = {
        "revenue": 15000.0,
        "cogs": 7500.0,           # COGS - Services
        "gross_margin": 7500.0,   # Revenue - COGS
        "overheads": 5100.0,      # All overhead components
        "ebit": 2400.0,           # Gross Margin - Overheads
    }

    print("\n[METRICS] CALCULATED METRICS:")
    print(f"Revenue:       {metrics['revenue']:>10.2f} (expected: {expected['revenue']:.2f})")
    print(f"COGS:          {metrics['cogs']:>10.2f} (expected: {expected['cogs']:.2f})")
    print(f"Gross Margin:  {metrics['gross_margin']:>10.2f} (expected: {expected['gross_margin']:.2f})")
    print(f"Overheads:     {metrics['overheads']:>10.2f} (expected: {expected['overheads']:.2f})")
    print(f"EBIT:          {metrics['ebit']:>10.2f} (expected: {expected['ebit']:.2f})")

    # Verify
    errors = []
    for key, expected_value in expected.items():
        actual = metrics[key]
        if abs(actual - expected_value) > 0.01:
            errors.append(f"[ERR] {key}: expected {expected_value}, got {actual}")

    if errors:
        print("\n[ERR] ERRORS:")
        for err in errors:
            print(f"  {err}")
        return False
    else:
        print("\n[OK] ALL TESTS PASSED!")
        return True


if __name__ == "__main__":
    print("\nTESTING CHART DATA CALCULATIONS\n")

    vision_ok = test_vision_parser_format()
    legacy_ok = test_legacy_format()

    print("\n" + "=" * 80)
    if vision_ok and legacy_ok:
        print("[OK] ALL TESTS PASSED - Grafy budou zobrazovat správné hodnoty!")
    else:
        print("[ERR] SOME TESTS FAILED - Zkontrolujte výpočty!")
    print("=" * 80)
