from django.core.management.base import BaseCommand

from ingest.models import FinancialStatement


class Command(BaseCommand):
    help = (
        "Remove stored overhead totals (Overheads/overheads) from FinancialStatement.income. "
        "Overheads are now derived from detailed components; values are expected in CZK."
    )

    def handle(self, *args, **options):
        updated = 0
        for fs in FinancialStatement.objects.all():
            income = fs.income or {}
            if "Overheads" in income or "overheads" in income:
                payload = dict(income)
                payload.pop("Overheads", None)
                payload.pop("overheads", None)
                fs.income = payload
                fs.save(update_fields=["income"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Updated {updated} statements."))
