from django.db import migrations, models


INCOME_TYPES = {"income_statement", "income", "vysledovka"}
BALANCE_TYPES = {"balance_sheet", "balance", "rozvaha"}


def merge_statements(apps, schema_editor):
    FinancialStatement = apps.get_model("ingest", "FinancialStatement")

    grouped = {}
    for fs in FinancialStatement.objects.all().order_by("id"):
        key = (fs.user_id, fs.year)
        grouped.setdefault(key, []).append(fs)

    for (_user_id, year), statements in grouped.items():
        if not statements:
            continue

        target = statements[0]
        income_data = getattr(target, "income", None)
        balance_data = getattr(target, "balance", None)
        scale_value = None

        for stmt in statements:
            doc_type = (getattr(stmt, "doc_type", "") or "").lower()
            payload = getattr(stmt, "data", None)

            if doc_type in INCOME_TYPES:
                if income_data is None and payload:
                    income_data = payload
            elif doc_type in BALANCE_TYPES:
                if balance_data is None and payload:
                    balance_data = payload
            else:
                if income_data is None and payload:
                    income_data = payload

            if scale_value is None and getattr(stmt, "scale", None):
                scale_value = stmt.scale

        target.income = income_data
        target.balance = balance_data
        target.scale = scale_value or "thousands"
        target.save(update_fields=["income", "balance", "scale"])

        for extra in statements[1:]:
            extra.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ingest", "0006_align_models"),
    ]

    operations = [
        migrations.RenameField(
            model_name="financialstatement",
            old_name="owner",
            new_name="user",
        ),
        migrations.AddField(
            model_name="financialstatement",
            name="balance",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="financialstatement",
            name="income",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="financialstatement",
            name="scale",
            field=models.CharField(default="thousands", max_length=20),
        ),
        migrations.RunPython(
            code=merge_statements,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterUniqueTogether(
            name="financialstatement",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="financialstatement",
            name="data",
        ),
        migrations.RemoveField(
            model_name="financialstatement",
            name="doc_type",
        ),
        migrations.AddConstraint(
            model_name="financialstatement",
            constraint=models.UniqueConstraint(
                fields=("user", "year"),
                name="unique_statement_per_user_year",
            ),
        ),
    ]
