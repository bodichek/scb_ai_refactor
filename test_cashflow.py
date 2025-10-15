#!/usr/bin/env python
"""
Testovací skript pro ověření cashflow dat
"""
import os
import django

# Nastavení Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from ingest.models import FinancialStatement
from dashboard.cashflow import calculate_cashflow

def test_cashflow():
    print("🔍 Kontrola uživatelů...")
    users = User.objects.all()
    print(f"Počet uživatelů: {users.count()}")
    
    for user in users:
        print(f"\n👤 Uživatel: {user.username}")
        
        # Kontrola finančních výkazů
        statements = FinancialStatement.objects.filter(owner=user)
        print(f"Počet finančních výkazů: {statements.count()}")
        
        for statement in statements:
            print(f"📊 Rok: {statement.year}")
            print(f"Data: {statement.data}")
            
            # Test cashflow
            cf = calculate_cashflow(user, statement.year)
            if cf:
                print(f"✅ Cashflow pro rok {statement.year}:")
                print(f"  - Net profit: {cf.get('net_profit', 'N/A')}")
                print(f"  - Depreciation: {cf.get('depreciation', 'N/A')}")
                print(f"  - Working capital change: {cf.get('working_capital_change', 'N/A')}")
                print(f"  - Operating CF: {cf.get('operating_cf', 'N/A')}")
                print(f"  - CapEx: {cf.get('capex', 'N/A')}")
                print(f"  - Asset sales: {cf.get('asset_sales', 'N/A')}")
                print(f"  - Investing CF: {cf.get('investing_cf', 'N/A')}")
                print(f"  - Loans received: {cf.get('loans_received', 'N/A')}")
                print(f"  - Loans repaid: {cf.get('loans_repaid', 'N/A')}")
                print(f"  - Financing CF: {cf.get('financing_cf', 'N/A')}")
                print(f"  - Net cash flow: {cf.get('net_cash_flow', 'N/A')}")
                print(f"  - Cash begin: {cf.get('cash_begin', 'N/A')}")
                print(f"  - Cash end: {cf.get('cash_end', 'N/A')}")
            else:
                print(f"❌ Cashflow pro rok {statement.year} se nepodařilo vypočítat")

if __name__ == "__main__":
    test_cashflow()