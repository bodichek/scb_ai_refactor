#!/usr/bin/env python
"""Simple test of vision parser data flow to dashboard"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from finance.utils import compute_metrics

# Mock FinancialStatement object
class MockFS:
    def __init__(self, income, balance):
        self.income = income
        self.balance = balance
        self.scale = "thousands"

# Simulated vision parser output (after post-processing)
mock_data = {
    "income": {
        # Raw components from PDF (in thousands after conversion)
        "revenue_products_services": 20.037,
        "revenue_goods": 0.330,
        "revenue": 20.367,  # Computed by vision parser
        "cogs_goods": 10.0,
        "cogs_materials": 5.0,
        "cogs": 15.0,  # Computed by vision parser
        "services": 2.0,
        "personnel_wages": 5.0,
        "personnel_insurance": 0.8,
        "taxes_fees": 0.5,
        "depreciation": 1.2,
        "other_operating_costs": 1.5,
    },
    "balance": {}
}

fs = MockFS(mock_data["income"], mock_data["balance"])
metrics = compute_metrics(fs)

print("="*70)
print("VISION PARSER -> DASHBOARD DATA FLOW TEST")
print("="*70)
print()
print("1. INPUT (Vision Parser Output):")
print(f"   revenue_products_services: {mock_data['income']['revenue_products_services']} tis.")
print(f"   revenue_goods: {mock_data['income']['revenue_goods']} tis.")
print(f"   revenue (computed): {mock_data['income']['revenue']} tis.")
print()
print("2. DASHBOARD METRICS (from compute_metrics):")
print(f"   Revenue: {metrics['revenue']:.3f} tis.")
print(f"   COGS: {metrics['cogs']:.3f} tis.")
print(f"   Overheads: {metrics['overheads']:.3f} tis.")
print(f"   Gross Margin: {metrics['gross_margin']:.3f} tis.")
print(f"   EBIT: {metrics['ebit']:.3f} tis.")
print(f"   Net Profit: {metrics['net_profit']:.3f} tis.")
print()
print("3. PROFITABILITY RATIOS:")
print(f"   Gross Margin %: {metrics['profitability']['gm_pct']:.1f}%")
print(f"   Operating Margin %: {metrics['profitability']['op_pct']:.1f}%")
print(f"   Net Profit %: {metrics['profitability']['np_pct']:.1f}%")
print()

# Validation
expected_revenue = 20.037 + 0.330
expected_overheads = 2.0 + 5.0 + 0.8 + 0.5 + 1.2 + 1.5

checks = [
    ("Revenue", abs(metrics['revenue'] - expected_revenue) < 0.01),
    ("Overheads", abs(metrics['overheads'] - expected_overheads) < 0.01),
]

print("4. VALIDATION:")
all_ok = True
for name, passed in checks:
    status = "OK" if passed else "FAIL"
    print(f"   [{status}] {name}")
    if not passed:
        all_ok = False

print()
if all_ok:
    print("SUCCESS: All checks passed! Vision data flows correctly to dashboard.")
else:
    print("ERROR: Some checks failed!")
    sys.exit(1)
