import json
from typing import Any, Dict, Iterable, Optional

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from finance.utils import compute_metrics, compute_overheads, first_number
from ingest.models import FinancialStatement


def _get_metric(data: Dict[str, Any], keys: Iterable[str]) -> Optional[float]:
    return first_number(data or {}, keys)


def _cogs_without_services(data: Dict[str, Any]) -> Optional[float]:
    cogs = _get_metric(data, ("COGS", "cogs"))
    services = _get_metric(data, ("services", "Services"))
    if cogs is None:
        return None
    if services is not None and services > 0 and cogs > 0:
        return max(cogs - services, 0.0)
    return cogs


class Command(BaseCommand):
    help = (
        "Diagnostika uloženého výkazu: vypíše základní hodnoty a odvozené metriky "
        "pro vybraného uživatele a rok."
    )

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, help="ID uživatele")
        parser.add_argument("--email", type=str, help="Email uživatele (alternativa k user-id)")
        parser.add_argument("--username", type=str, help="Username uživatele (alternativa k user-id)")
        parser.add_argument("--year", type=int, required=True, help="Rok výkazu")

    def handle(self, *args, **options):
        user = self._resolve_user(options)
        year = options["year"]

        fs = (
            FinancialStatement.objects.filter(user=user, year=year)
            .order_by("-created_at")
            .first()
        )
        if not fs:
            raise CommandError(f"Nenalezen FinancialStatement pro uživatele {user} a rok {year}.")

        income = fs.income or {}
        balance = fs.balance or {}
        metrics = compute_metrics(fs)

        services = _get_metric(income, ("services", "Services"))
        cogs_adjusted = _cogs_without_services(income)
        cogs_goods = _get_metric(income, ("cogs_goods",))
        cogs_materials = _get_metric(income, ("cogs_materials",))

        overheads = compute_overheads(income)
        overhead_components = {
            "services": services,
            "personnel_wages": _get_metric(income, ("personnel_wages", "PersonnelWages")),
            "personnel_insurance": _get_metric(income, ("personnel_insurance", "PersonnelInsurance")),
            "taxes_fees": _get_metric(income, ("taxes_fees", "TaxesFees")),
            "depreciation": _get_metric(income, ("depreciation", "Depreciation")),
            "other_operating_costs": _get_metric(income, ("other_operating_costs", "OtherOperatingCosts")),
            "stored_overheads": _get_metric(income, ("Overheads", "overheads")),
        }

        payload = {
            "user": str(user),
            "year": year,
            "raw_fields": {
                "Revenue": metrics["revenue"],
                "COGS": _get_metric(income, ("COGS", "cogs")),
                "services": services,
                "cogs_goods": cogs_goods,
                "cogs_materials": cogs_materials,
                "Overheads": overhead_components["stored_overheads"],
            },
            "derived": {
                "cogs_without_services": cogs_adjusted,
                "overheads_total": overheads,
                "overhead_components": overhead_components,
                "gross_margin": metrics["gross_margin"],
            },
            "datasets": {
                "income": income,
                "balance": balance,
            },
        }

        self.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))

    def _resolve_user(self, options):
        User = get_user_model()
        user_id = options.get("user_id")
        email = options.get("email")
        username = options.get("username")

        try:
            if user_id:
                return User.objects.get(id=user_id)
            if email:
                return User.objects.get(email=email)
            if username:
                return User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError("Uživatel nenalezen podle zadaného identifikátoru.")

        raise CommandError("Zadej --user-id nebo --email nebo --username.")
