"""
Test všech dashboard komponent - Growth, Profitability Margins.
Ověřuje, že všechny vzorce odpovídají specifikaci uživatele.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from finance.utils import compute_metrics, growth


def test_all_components():
    """Test všech komponent - Growth a Profitability Margins."""

    # Simulace dat pro 2 roky
    class MockFS_2023:
        def __init__(self):
            self.income = {
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
            }
            self.balance = {}

    class MockFS_2024:
        def __init__(self):
            self.income = {
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
            }
            self.balance = {}

    # Výpočet metrik
    fs_2023 = MockFS_2023()
    fs_2024 = MockFS_2024()

    metrics_2023 = compute_metrics(fs_2023)
    metrics_2024 = compute_metrics(fs_2024)

    print("=" * 80)
    print("TEST: Všechny Dashboard Komponenty")
    print("=" * 80)

    # === ČÁST 1: Základní metriky ===
    print("\n[METRIKY] ROK 2023:")
    print(f"  Revenue:      {metrics_2023['revenue']:>10.2f} (očekáváno: 20500.00)")
    print(f"  COGS:         {metrics_2023['cogs']:>10.2f} (očekáváno: 9800.00)")
    print(f"  Gross Margin: {metrics_2023['gross_margin']:>10.2f} (očekáváno: 10700.00)")
    print(f"  Overheads:    {metrics_2023['overheads']:>10.2f} (očekáváno: 6400.00)")
    print(f"  EBIT:         {metrics_2023['ebit']:>10.2f} (očekáváno: 4300.00)")
    print(f"  Net Profit:   {metrics_2023['net_profit']:>10.2f} (očekáváno: 3900.00)")

    print("\n[METRIKY] ROK 2024:")
    print(f"  Revenue:      {metrics_2024['revenue']:>10.2f} (očekáváno: 24000.00)")
    print(f"  COGS:         {metrics_2024['cogs']:>10.2f} (očekáváno: 11000.00)")
    print(f"  Gross Margin: {metrics_2024['gross_margin']:>10.2f} (očekáváno: 13000.00)")
    print(f"  Overheads:    {metrics_2024['overheads']:>10.2f} (očekáváno: 7450.00)")
    print(f"  EBIT:         {metrics_2024['ebit']:>10.2f} (očekáváno: 5550.00)")
    print(f"  Net Profit:   {metrics_2024['net_profit']:>10.2f} (očekáváno: 4550.00)")

    # === ČÁST 2: Growth výpočty (YoY) ===
    rev_growth = growth(metrics_2024["revenue"], metrics_2023["revenue"])
    cogs_growth = growth(metrics_2024["cogs"], metrics_2023["cogs"])
    overheads_growth = growth(metrics_2024["overheads"], metrics_2023["overheads"])

    print("\n[GROWTH] Year-over-Year (2024 vs 2023):")
    print(f"  Revenue Growth:    {rev_growth:>6.2f}% (vzorec: (24000-20500)/20500*100)")
    print(f"  COGS Growth:       {cogs_growth:>6.2f}% (vzorec: (11000-9800)/9800*100)")
    print(f"  Overheads Growth:  {overheads_growth:>6.2f}% (vzorec: (7450-6400)/6400*100)")

    # Manuální výpočet expected values
    expected_rev_growth = (24000.0 - 20500.0) / 20500.0 * 100.0
    expected_cogs_growth = (11000.0 - 9800.0) / 9800.0 * 100.0
    expected_overheads_growth = (7450.0 - 6400.0) / 6400.0 * 100.0

    print(f"\n  Expected Revenue Growth:    {expected_rev_growth:>6.2f}%")
    print(f"  Expected COGS Growth:       {expected_cogs_growth:>6.2f}%")
    print(f"  Expected Overheads Growth:  {expected_overheads_growth:>6.2f}%")

    # === ČÁST 3: Profitability Margins ===
    print("\n[PROFITABILITY] 2023:")
    print(f"  Gross Margin %:     {metrics_2023['profitability']['gm_pct']:>6.2f}% (vzorec: GM/Revenue*100)")
    print(f"  Operating Margin %: {metrics_2023['profitability']['op_pct']:>6.2f}% (vzorec: EBIT/Revenue*100)")
    print(f"  Net Margin %:       {metrics_2023['profitability']['np_pct']:>6.2f}% (vzorec: NP/Revenue*100)")

    print("\n[PROFITABILITY] 2024:")
    print(f"  Gross Margin %:     {metrics_2024['profitability']['gm_pct']:>6.2f}% (vzorec: GM/Revenue*100)")
    print(f"  Operating Margin %: {metrics_2024['profitability']['op_pct']:>6.2f}% (vzorec: EBIT/Revenue*100)")
    print(f"  Net Margin %:       {metrics_2024['profitability']['np_pct']:>6.2f}% (vzorec: NP/Revenue*100)")

    # Expected profitability margins
    expected_2023_gm_pct = (10700.0 / 20500.0) * 100.0
    expected_2023_op_pct = (4300.0 / 20500.0) * 100.0
    expected_2023_np_pct = (3900.0 / 20500.0) * 100.0

    expected_2024_gm_pct = (13000.0 / 24000.0) * 100.0
    expected_2024_op_pct = (5550.0 / 24000.0) * 100.0
    expected_2024_np_pct = (4550.0 / 24000.0) * 100.0

    print(f"\n  Expected 2023 - GM: {expected_2023_gm_pct:.2f}%, OP: {expected_2023_op_pct:.2f}%, NP: {expected_2023_np_pct:.2f}%")
    print(f"  Expected 2024 - GM: {expected_2024_gm_pct:.2f}%, OP: {expected_2024_op_pct:.2f}%, NP: {expected_2024_np_pct:.2f}%")

    # === ČÁST 4: Verifikace ===
    errors = []

    # Základní metriky 2023
    if abs(metrics_2023["revenue"] - 20500.0) > 0.01:
        errors.append(f"2023 Revenue: expected 20500.0, got {metrics_2023['revenue']}")
    if abs(metrics_2023["cogs"] - 9800.0) > 0.01:
        errors.append(f"2023 COGS: expected 9800.0, got {metrics_2023['cogs']}")
    if abs(metrics_2023["overheads"] - 6400.0) > 0.01:
        errors.append(f"2023 Overheads: expected 6400.0, got {metrics_2023['overheads']}")

    # Základní metriky 2024
    if abs(metrics_2024["revenue"] - 24000.0) > 0.01:
        errors.append(f"2024 Revenue: expected 24000.0, got {metrics_2024['revenue']}")
    if abs(metrics_2024["cogs"] - 11000.0) > 0.01:
        errors.append(f"2024 COGS: expected 11000.0, got {metrics_2024['cogs']}")
    if abs(metrics_2024["overheads"] - 7450.0) > 0.01:
        errors.append(f"2024 Overheads: expected 7450.0, got {metrics_2024['overheads']}")

    # Growth výpočty
    if abs(rev_growth - expected_rev_growth) > 0.01:
        errors.append(f"Revenue Growth: expected {expected_rev_growth:.2f}, got {rev_growth:.2f}")
    if abs(cogs_growth - expected_cogs_growth) > 0.01:
        errors.append(f"COGS Growth: expected {expected_cogs_growth:.2f}, got {cogs_growth:.2f}")
    if abs(overheads_growth - expected_overheads_growth) > 0.01:
        errors.append(f"Overheads Growth: expected {expected_overheads_growth:.2f}, got {overheads_growth:.2f}")

    # Profitability margins 2023
    if abs(metrics_2023["profitability"]["gm_pct"] - expected_2023_gm_pct) > 0.01:
        errors.append(f"2023 GM%: expected {expected_2023_gm_pct:.2f}, got {metrics_2023['profitability']['gm_pct']:.2f}")
    if abs(metrics_2023["profitability"]["op_pct"] - expected_2023_op_pct) > 0.01:
        errors.append(f"2023 OP%: expected {expected_2023_op_pct:.2f}, got {metrics_2023['profitability']['op_pct']:.2f}")
    if abs(metrics_2023["profitability"]["np_pct"] - expected_2023_np_pct) > 0.01:
        errors.append(f"2023 NP%: expected {expected_2023_np_pct:.2f}, got {metrics_2023['profitability']['np_pct']:.2f}")

    # Profitability margins 2024
    if abs(metrics_2024["profitability"]["gm_pct"] - expected_2024_gm_pct) > 0.01:
        errors.append(f"2024 GM%: expected {expected_2024_gm_pct:.2f}, got {metrics_2024['profitability']['gm_pct']:.2f}")
    if abs(metrics_2024["profitability"]["op_pct"] - expected_2024_op_pct) > 0.01:
        errors.append(f"2024 OP%: expected {expected_2024_op_pct:.2f}, got {metrics_2024['profitability']['op_pct']:.2f}")
    if abs(metrics_2024["profitability"]["np_pct"] - expected_2024_np_pct) > 0.01:
        errors.append(f"2024 NP%: expected {expected_2024_np_pct:.2f}, got {metrics_2024['profitability']['np_pct']:.2f}")

    if errors:
        print("\n[ERR] ERRORS DETECTED:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("\n" + "=" * 80)
        print("[OK] VŠECHNY KOMPONENTY FUNGUJÍ SPRÁVNĚ!")
        print("=" * 80)
        return True


if __name__ == "__main__":
    print("\nTESTING ALL DASHBOARD COMPONENTS\n")
    success = test_all_components()
    sys.exit(0 if success else 1)
