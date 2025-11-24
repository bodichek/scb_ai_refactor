import json
from typing import Any, Dict, Iterable, Optional

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from finance.utils import compute_overheads, first_number, to_number
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
        "Diagnostika uloženého výkazu: vypíše surová pole a odvozené hodnoty "
        "(COGS, services, overheads) pro vybraného uživatele a rok."
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
            FinancialStatement.objects.filter(owner=user, year=year)
            .order_by("-created_at")
            .first()
        )
        if not fs:
            raise CommandError(f"Nenalezen FinancialStatement pro uživatele {user} a rok {year}.")

        data = fs.data or {}

        revenue = _get_metric(data, ("Revenue", "revenue"))
        cogs_raw = _get_metric(data, ("COGS", "cogs"))
        services = _get_metric(data, ("services", "Services"))
        cogs_adjusted = _cogs_without_services(data)
        cogs_goods = _get_metric(data, ("cogs_goods",))
        cogs_materials = _get_metric(data, ("cogs_materials",))

        overheads = compute_overheads(data)
        overhead_components = {
            "services": services,
            "personnel_wages": _get_metric(data, ("personnel_wages", "PersonnelWages")),
            "personnel_insurance": _get_metric(data, ("personnel_insurance", "PersonnelInsurance")),
            "taxes_fees": _get_metric(data, ("taxes_fees", "TaxesFees")),
            "depreciation": _get_metric(data, ("depreciation", "Depreciation")),
            "other_operating_costs": _get_metric(
                data, ("other_operating_costs", "OtherOperatingCosts")
            ),
            "stored_overheads": _get_metric(data, ("Overheads", "overheads")),
        }

        payload = {
            "user": str(user),
            "year": year,
            "raw_fields": {
                "Revenue": revenue,
                "COGS": cogs_raw,
                "services": services,
                "cogs_goods": cogs_goods,
                "cogs_materials": cogs_materials,
                "Overheads": overhead_components["stored_overheads"],
            },
            "derived": {
                "cogs_without_services": cogs_adjusted,
                "overheads_total": overheads,
                "overhead_components": overhead_components,
                "gross_margin": (revenue - cogs_adjusted) if (revenue is not None and cogs_adjusted is not None) else None,
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
