from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase

from dashboard.cashflow import calculate_cashflow
from finance.utils import compute_overheads, compute_profitability, growth
from ingest.models import Document, FinancialStatement


class FinanceUtilsTests(SimpleTestCase):
    def test_compute_overheads_prefers_components(self):
        data = {
            "Overheads": 999,
            "services": 30,
            "personnel_wages": 20,
            "taxes_fees": 10,
            "depreciation": 50,
        }
        self.assertEqual(compute_overheads(data), 110)

    def test_compute_overheads_fallback_to_total(self):
        data = {"Overheads": 250}
        self.assertEqual(compute_overheads(data), 250)

    def test_profitability_and_growth_helpers(self):
        profitability = compute_profitability(1000, 600, 400, 300)
        self.assertAlmostEqual(profitability["gm_pct"], 60.0)
        self.assertAlmostEqual(profitability["op_pct"], 40.0)
        self.assertAlmostEqual(profitability["np_pct"], 30.0)

        self.assertIsNone(growth(100, 0))
        self.assertAlmostEqual(growth(120, 100), 20.0)


class CashflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="tester")
        upload = SimpleUploadedFile("test.pdf", b"x")
        self.document = Document.objects.create(
            owner=self.user,
            file=upload,
            year=2024,
            doc_type="income",
            analyzed=True,
        )

    def test_calculate_cashflow_basic(self):
        statement_data = {
            "Revenue": 1000,
            "COGS": 400,
            "services": 30,
            "personnel_wages": 20,
            "taxes_fees": 10,
            "depreciation": 50,
            "Cash": 100,
            "CapEx": 20,
        }
        FinancialStatement.objects.create(
            user=self.user,
            document=self.document,
            year=2024,
            income=statement_data,
        )

        cf = calculate_cashflow(self.user, 2024)
        self.assertIsNotNone(cf)
        self.assertAlmostEqual(cf["overheads"], 110.0)
        self.assertAlmostEqual(cf["net_profit"], 490.0)
        self.assertAlmostEqual(cf["operating_cf"], 540.0)
        self.assertAlmostEqual(cf["investing_cf"], -20.0)
        self.assertAlmostEqual(cf["cash_end"], 600.0)
