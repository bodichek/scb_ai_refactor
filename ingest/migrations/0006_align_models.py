from django.db import migrations, models

DOC_TYPES = [
    ("income_statement", "Income Statement"),
    ("balance_sheet", "Balance Sheet"),
    ("income", "Income Statement (legacy)"),
    ("balance", "Balance Sheet (legacy)"),
    ("rozvaha", "Rozvaha (legacy)"),
    ("vysledovka", "Vysledovka (legacy)"),
    ("cashflow", "Cash Flow"),
    ("other", "Other"),
]


def _backfill_financial_statements(apps, schema_editor):
    FinancialStatement = apps.get_model("ingest", "FinancialStatement")
    Document = apps.get_model("ingest", "Document")

    for fs in FinancialStatement.objects.all().iterator():
        doc_type = (
            Document.objects.filter(id=fs.document_id)
            .values_list("doc_type", flat=True)
            .first()
        )
        fs.doc_type = doc_type or "other"
        if not getattr(fs, "scale", None):
            fs.scale = "units"
        fs.save(update_fields=["doc_type", "scale"])


class Migration(migrations.Migration):

    dependencies = [
        ("ingest", "0005_document_description_document_filename"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="year",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="document",
            name="doc_type",
            field=models.CharField(
                blank=True,
                choices=DOC_TYPES,
                default="other",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="financialstatement",
            name="doc_type",
            field=models.CharField(
                choices=DOC_TYPES,
                default="other",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="financialstatement",
            name="scale",
            field=models.CharField(default="units", max_length=20),
        ),
        migrations.RunPython(
            code=_backfill_financial_statements,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterUniqueTogether(
            name="financialstatement",
            unique_together={("owner", "year", "doc_type")},
        ),
    ]


def _backfill_financial_statements(apps):
    FinancialStatement = apps.get_model("ingest", "FinancialStatement")
    Document = apps.get_model("ingest", "Document")

    for fs in FinancialStatement.objects.all().iterator():
        doc_type = (
            Document.objects.filter(id=fs.document_id)
            .values_list("doc_type", flat=True)
            .first()
        )
        fs.doc_type = doc_type or "other"
        if not getattr(fs, "scale", None):
            fs.scale = "units"
        fs.save(update_fields=["doc_type", "scale"])
