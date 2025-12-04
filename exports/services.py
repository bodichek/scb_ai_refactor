from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.db import transaction

from ingest.models import FinancialStatement
from finance.utils import compute_metrics, growth

from .models import Export


@dataclass
class ExportData:
    payload: Dict[str, Any]
    statement_year: Optional[int]


def build_latest_export_payload(user) -> Optional[ExportData]:
    """
    Builds a numeric payload for the most recent financial statement of the user.
    Returns None if there are no statements.
    """

    statements = list(
        FinancialStatement.objects.filter(user=user).order_by("-year")
    )
    if not statements:
        return None

    latest = statements[0]
    latest_metrics = compute_metrics(latest)

    prev_metrics = compute_metrics(statements[1]) if len(statements) > 1 else None
    prev_revenue = prev_metrics["revenue"] if prev_metrics else None

    revenue_growth_yoy = growth(latest_metrics["revenue"], prev_revenue)

    revenue_history = []
    for stmt in sorted(statements, key=lambda s: s.year):
        metrics = compute_metrics(stmt)
        value = metrics["revenue"]
        if value is not None:
            revenue_history.append(
                {
                    "year": int(stmt.year),
                    "Revenue": value,
                }
            )

    payload: Dict[str, Any] = {
        "year": int(latest.year),
        "Revenue": latest_metrics["revenue"],
        "COGS": latest_metrics["cogs"],
        "GrossMargin": latest_metrics["gross_margin"],
        "Overheads": latest_metrics["overheads"],
        "Depreciation": latest_metrics["depreciation"],
        "EBIT": latest_metrics["ebit"],
        "NetProfit": latest_metrics["net_profit"],
        "RevenueGrowthYoY": revenue_growth_yoy,
        "EBITMargin": latest_metrics["profitability"]["op_pct"],
        "NetProfitMargin": latest_metrics["profitability"]["np_pct"],
    }

    if revenue_history:
        payload["RevenueHistory"] = revenue_history

    return ExportData(payload=payload, statement_year=int(latest.year))


@transaction.atomic
def generate_export(user) -> Optional[Export]:
    """
    Generates and persists a new export snapshot for the user.
    Returns the created Export instance or None if source data are unavailable.
    """

    snapshot = build_latest_export_payload(user)
    if not snapshot:
        return None

    return Export.objects.create(
        user=user,
        statement_year=snapshot.statement_year,
        data=snapshot.payload,
        source=Export.SOURCE_DASHBOARD,
    )


def get_latest_export(user, ensure_exists: bool = True) -> Optional[Export]:
    """
    Returns the most recent export record. Optionally generates one if missing.
    """

    export = Export.objects.filter(user=user).order_by("-created_at").first()
    if export or not ensure_exists:
        return export

    return generate_export(user)
