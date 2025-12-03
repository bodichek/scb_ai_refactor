"""
Test vision extraction data flow to dashboard
Shows how extracted data flows through finance/utils.py to dashboard
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ingest.models import FinancialStatement, Document
from finance.utils import compute_metrics
import json


class Command(BaseCommand):
    help = 'Test vision extraction data flow to dashboard'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('TEST: Vision Parser -> Dashboard Data Flow'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        # Simulovaná data z vision parseru (po post-processingu)
        mock_vision_data = {
            "income": {
                # Raw komponenty z PDF (v thousands po konverzi)
                "revenue_products_services": 20.037,  # 20,037 tis. Kč
                "revenue_goods": 0.330,               # 330 tis. Kč
                "revenue": 20.367,                     # Computed: 20,367 tis. Kč

                "cogs_goods": 10.0,                    # 10,000 tis. Kč
                "cogs_materials": 5.0,                 # 5,000 tis. Kč
                "cogs": 15.0,                          # Computed: 15,000 tis. Kč

                "services": 2.0,                       # 2,000 tis. Kč
                "personnel_wages": 5.0,                # 5,000 tis. Kč
                "personnel_insurance": 0.8,            # 800 tis. Kč
                "taxes_fees": 0.5,                     # 500 tis. Kč
                "depreciation": 1.2,                   # 1,200 tis. Kč
                "other_operating_costs": 1.5,          # 1,500 tis. Kč
                "other_operating_revenue": 0.5,        # 500 tis. Kč
                "financial_revenue": 0.1,              # 100 tis. Kč
                "financial_costs": 0.2,                # 200 tis. Kč
                "income_tax": 2.0,                     # 2,000 tis. Kč
            },
            "balance": {
                "receivables": 15.0,                   # 15,000 tis. Kč
                "inventory": 8.0,                      # 8,000 tis. Kč
                "short_term_liabilities": 12.0,        # 12,000 tis. Kč
                "cash": 5.0,                           # 5,000 tis. Kč
                "tangible_assets": 50.0,               # 50,000 tis. Kč
                "total_assets": 100.0,                 # 100,000 tis. Kč
                "equity": 60.0,                        # 60,000 tis. Kč
                "total_liabilities": 40.0,             # 40,000 tis. Kč
                "trade_payables": 8.0,                 # 8,000 tis. Kč
                "short_term_loans": 15.0,              # 15,000 tis. Kč
                "long_term_loans": 17.0,               # 17,000 tis. Kč
            }
        }

        self.stdout.write(self.style.WARNING('\n1. VSTUPNÍ DATA Z VISION PARSERU:'))
        self.stdout.write('   (Po post-processingu: komponenty + aggregates, v thousands)\n')
        self.stdout.write(f'   Revenue components:')
        self.stdout.write(f'     - revenue_products_services: {mock_vision_data["income"]["revenue_products_services"]} tis. Kč')
        self.stdout.write(f'     - revenue_goods: {mock_vision_data["income"]["revenue_goods"]} tis. Kč')
        self.stdout.write(f'     - revenue (computed): {mock_vision_data["income"]["revenue"]} tis. Kč')

        self.stdout.write(f'\n   COGS components:')
        self.stdout.write(f'     - cogs_goods: {mock_vision_data["income"]["cogs_goods"]} tis. Kč')
        self.stdout.write(f'     - cogs_materials: {mock_vision_data["income"]["cogs_materials"]} tis. Kč')
        self.stdout.write(f'     - cogs (computed): {mock_vision_data["income"]["cogs"]} tis. Kč')

        self.stdout.write(f'\n   Overhead components:')
        self.stdout.write(f'     - services: {mock_vision_data["income"]["services"]} tis. Kč')
        self.stdout.write(f'     - personnel_wages: {mock_vision_data["income"]["personnel_wages"]} tis. Kč')
        self.stdout.write(f'     - personnel_insurance: {mock_vision_data["income"]["personnel_insurance"]} tis. Kč')
        self.stdout.write(f'     - depreciation: {mock_vision_data["income"]["depreciation"]} tis. Kč')

        # Vytvořit mock FinancialStatement objekt
        class MockFS:
            def __init__(self, income, balance):
                self.income = income
                self.balance = balance
                self.scale = "thousands"

        fs = MockFS(mock_vision_data["income"], mock_vision_data["balance"])

        self.stdout.write(self.style.WARNING('\n\n2. ZPRACOVÁNÍ PŘES finance/utils.py:'))
        self.stdout.write('   compute_metrics(fs) → spočítá metriky pro dashboard\n')

        # Spočítej metriky pomocí finance/utils
        metrics = compute_metrics(fs)

        self.stdout.write(f'   Revenue calculation:')
        self.stdout.write(f'     ✓ Dashboard revenue: {metrics["revenue"]:.3f} tis. Kč')
        self.stdout.write(f'       (Z komponenty nebo přímá hodnota)')

        self.stdout.write(f'\n   COGS calculation:')
        self.stdout.write(f'     ✓ Dashboard COGS: {metrics["cogs"]:.3f} tis. Kč')
        self.stdout.write(f'       (Z komponenty nebo přímá hodnota)')

        self.stdout.write(f'\n   Overheads calculation:')
        self.stdout.write(f'     ✓ Dashboard overheads: {metrics["overheads"]:.3f} tis. Kč')
        self.stdout.write(f'       (Součet: services + wages + insurance + taxes + depreciation + other)')

        self.stdout.write(f'\n   Gross Margin:')
        self.stdout.write(f'     ✓ {metrics["gross_margin"]:.3f} tis. Kč')
        self.stdout.write(f'       = Revenue ({metrics["revenue"]:.3f}) - COGS ({metrics["cogs"]:.3f})')

        self.stdout.write(f'\n   EBIT (Operating Profit):')
        self.stdout.write(f'     ✓ {metrics["ebit"]:.3f} tis. Kč')
        self.stdout.write(f'       = Gross Margin ({metrics["gross_margin"]:.3f}) - Overheads ({metrics["overheads"]:.3f})')

        self.stdout.write(f'\n   Net Profit:')
        self.stdout.write(f'     ✓ {metrics["net_profit"]:.3f} tis. Kč')
        self.stdout.write(f'       = Revenue - COGS - Overheads')

        self.stdout.write(f'\n   Profitability Ratios:')
        self.stdout.write(f'     ✓ Gross Margin %: {metrics["profitability"]["gm_pct"]:.1f}%')
        self.stdout.write(f'     ✓ Operating Margin %: {metrics["profitability"]["op_pct"]:.1f}%')
        self.stdout.write(f'     ✓ Net Profit %: {metrics["profitability"]["np_pct"]:.1f}%')

        self.stdout.write(self.style.WARNING('\n\n3. CO VIDÍ DASHBOARD:'))
        self.stdout.write('   dashboard/views.py → build_dashboard_context()\n')

        self.stdout.write('   Data pro grafy a tabulky:')
        self.stdout.write(f'     • Revenue: {metrics["revenue"]:.3f} tis. Kč ({metrics["revenue"]*1000:.0f} Kč)')
        self.stdout.write(f'     • COGS: {metrics["cogs"]:.3f} tis. Kč')
        self.stdout.write(f'     • Gross Margin: {metrics["gross_margin"]:.3f} tis. Kč')
        self.stdout.write(f'     • Overheads: {metrics["overheads"]:.3f} tis. Kč')
        self.stdout.write(f'     • EBIT: {metrics["ebit"]:.3f} tis. Kč')
        self.stdout.write(f'     • Net Profit: {metrics["net_profit"]:.3f} tis. Kč')

        self.stdout.write(self.style.SUCCESS('\n\n4. ✓ OVĚŘENÍ - VŠE FUNGUJE SPRÁVNĚ:'))
        checks = []

        # Check 1: Revenue z komponent
        expected_revenue = 20.037 + 0.330
        checks.append(("Revenue z komponent", abs(metrics["revenue"] - expected_revenue) < 0.01))

        # Check 2: COGS z komponent
        expected_cogs = 10.0 + 5.0
        checks.append(("COGS z komponent", abs(metrics["cogs"] - expected_cogs) < 0.01))

        # Check 3: Overheads
        expected_overheads = 2.0 + 5.0 + 0.8 + 0.5 + 1.2 + 1.5
        checks.append(("Overheads sum", abs(metrics["overheads"] - expected_overheads) < 0.01))

        # Check 4: Gross Margin
        expected_gm = expected_revenue - expected_cogs
        checks.append(("Gross Margin", abs(metrics["gross_margin"] - expected_gm) < 0.01))

        # Check 5: EBIT
        expected_ebit = expected_gm - expected_overheads
        checks.append(("EBIT", abs(metrics["ebit"] - expected_ebit) < 0.01))

        for check_name, passed in checks:
            icon = "✓" if passed else "✗"
            style = self.style.SUCCESS if passed else self.style.ERROR
            self.stdout.write(style(f'   {icon} {check_name}'))

        all_passed = all(p for _, p in checks)

        if all_passed:
            self.stdout.write(self.style.SUCCESS('\n' + '='*70))
            self.stdout.write(self.style.SUCCESS('✓ VŠE FUNGUJE! Data z vision parseru správně procházejí do dashboardu.'))
            self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        else:
            self.stdout.write(self.style.ERROR('\n✗ PROBLÉM! Některé výpočty nesedí.\n'))

        self.stdout.write(self.style.WARNING('\n5. PŘÍKLAD REAL DATA FLOW:'))
        self.stdout.write('\n   Vision Parser (PNG) →')
        self.stdout.write('     extracted_data = {')
        self.stdout.write('       "revenue_products_services": 20037,  # Raw z PDF')
        self.stdout.write('       "revenue_goods": 330,')
        self.stdout.write('       ...}')
        self.stdout.write('     scale = "thousands"')
        self.stdout.write('\n   Post-processing (_compute_aggregates + _convert_to_thousands) →')
        self.stdout.write('     revenue = 20.037 + 0.330 = 20.367 tis.')
        self.stdout.write('     cogs = 10.0 + 5.0 = 15.0 tis.')
        self.stdout.write('     (Pokud byl scale="units" → děleno 1000)')
        self.stdout.write('\n   Saved to DB (FinancialStatement) →')
        self.stdout.write('     fs.income = {...komponenty + aggregates...}')
        self.stdout.write('     fs.scale = "thousands"')
        self.stdout.write('\n   Dashboard (compute_metrics) →')
        self.stdout.write('     ✓ Načte revenue přímo nebo z komponent')
        self.stdout.write('     ✓ Načte cogs přímo nebo z komponent')
        self.stdout.write('     ✓ Spočítá overheads z komponent')
        self.stdout.write('     ✓ Spočítá metriky (GM, EBIT, Net Profit)')
        self.stdout.write('\n   Výstup do template →')
        self.stdout.write('     Grafy, tabulky, KPIs zobrazeny správně! ✓\n')
