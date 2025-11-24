from django.core.management.base import BaseCommand

from ingest.models import FinancialStatement


class Command(BaseCommand):
    help = (
        "Remove stored overhead totals (Overheads/overheads) from FinancialStatement.data. "
        "Overheads are now derived from detailed components; values in data are expected in CZK."
    )

    def handle(self, *args, **options):
        updated = 0
        for fs in FinancialStatement.objects.all():
            data = fs.data or {}
            if "Overheads" in data or "overheads" in data:
                payload = dict(data)
                payload.pop("Overheads", None)
                payload.pop("overheads", None)
                fs.data = payload
                fs.save(update_fields=["data"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Updated {updated} statements."))
