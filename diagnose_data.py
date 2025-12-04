"""
Diagnostic skript pro kontrolu dat v databázi.
Zobrazí skutečná data pro všechny roky a jejich výpočty.
"""

import os
import sys
import django
import json

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from accounts.models import User
from ingest.models import FinancialStatement
from finance.utils import compute_metrics, growth

print("=" * 100)
print("DIAGNOSTIC: Analýza dat v databázi")
print("=" * 100)

# Najít všechny uživatele s financial statements
users_with_data = User.objects.filter(financialstatement__isnull=False).distinct()

print(f"\nPočet uživatelů s daty: {users_with_data.count()}")

for user in users_with_data:
    statements = FinancialStatement.objects.filter(user=user).order_by('year')

    if statements.count() == 0:
        continue

    print(f"\n{'=' * 100}")
    print(f"USER: {user.username} (ID: {user.id})")
    print(f"{'=' * 100}")

    rows = []
    for stmt in statements:
        print(f"\n--- ROK {stmt.year} ---")
        print(f"Document: {stmt.document.filename if stmt.document else 'N/A'}")

        # Zobrazit income data
        if stmt.income:
            print(f"\nIncome keys: {list(stmt.income.keys())}")
            print(f"Income data:")
            for key, value in stmt.income.items():
                if value is not None and value != 0:
                    print(f"  {key}: {value}")
        else:
            print("Income: NONE")

        # Zobrazit balance data
        if stmt.balance:
            print(f"\nBalance keys: {list(stmt.balance.keys())}")
            balance_values = {k: v for k, v in stmt.balance.items() if v is not None and v != 0}
            if balance_values:
                print(f"Balance data (non-zero):")
                for key, value in balance_values.items():
                    print(f"  {key}: {value}")
        else:
            print("Balance: NONE")

        # Vypočítat metriky
        metrics = compute_metrics(stmt)
        print(f"\nVYPOČTENÉ METRIKY:")
        print(f"  Revenue:       {metrics['revenue']:>12.2f}")
        print(f"  COGS:          {metrics['cogs']:>12.2f}  {'<-- PROBLEM!' if metrics['cogs'] == 0 else ''}")
        print(f"  Gross Margin:  {metrics['gross_margin']:>12.2f}")
        print(f"  Overheads:     {metrics['overheads']:>12.2f}")
        print(f"  EBIT:          {metrics['ebit']:>12.2f}")
        print(f"  Net Profit:    {metrics['net_profit']:>12.2f}")

        rows.append({
            "year": stmt.year,
            "revenue": metrics["revenue"],
            "cogs": metrics["cogs"],
            "gross_margin": metrics["gross_margin"],
            "overheads": metrics["overheads"],
            "ebit": metrics["ebit"],
            "net_profit": metrics["net_profit"],
            "profitability": metrics["profitability"],
        })

    # Vypočítat growth
    print(f"\n{'=' * 100}")
    print("SOUHRN A GROWTH:")
    print(f"{'=' * 100}")
    print(f"{'Rok':<8} {'Tržby':>12} {'COGS':>12} {'Hrubá M.':>12} {'EBIT':>12} {'Růst T%':>10} {'Růst C%':>10}")
    print("-" * 100)

    for i, row in enumerate(rows):
        if i == 0:
            rev_growth = None
            cogs_growth = None
        else:
            prev = rows[i - 1]
            rev_growth = growth(row["revenue"], prev["revenue"])
            cogs_growth = growth(row["cogs"], prev["cogs"])

        print(f"{row['year']:<8} {row['revenue']:>12.2f} {row['cogs']:>12.2f} {row['gross_margin']:>12.2f} {row['ebit']:>12.2f} {rev_growth if rev_growth else '–':>10} {cogs_growth if cogs_growth else '–':>10}")

print(f"\n{'=' * 100}")
print("DOPORUČENÍ:")
print(f"{'=' * 100}")

print("""
Pokud vidíte COGS = 0:
1. Zkontrolujte, zda dokumenty obsahují řádky COGS ve výkazu zisku a ztráty
2. Pro Vision Parser formát musí být vyplněny:
   - cogs_goods (Náklady vynaložené na prodané zboží)
   - cogs_materials (Spotřeba materiálu a energie)
3. Pro Legacy formát musí být vyplněna hodnota:
   - cogs nebo COGS

Řešení:
- Nahrajte dokumenty znovu pomocí Vision Parseru
- Nebo ručně doplňte chybějící hodnoty v admin rozhraní
""")
