from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from django.db import transaction

from ingest.models import FinancialStatement
from finance.utils import compute_overheads, compute_profitability, first_number, growth

from .models import Export


@dataclass
class ExportData:
    payload: Dict[str, Any]
    statement_year: Optional[int]



def _prepare_metric(default_value: Optional[float], fallback: Optional[float] = None) -> Optional[float]:
    return default_value if default_value is not None else fallback


def _metric(data: Dict[str, Any], keys) -> Optional[float]:
    return first_number(data, keys)


def _cogs_without_services(data: Dict[str, Any]) -> Optional[float]:
    cogs = _metric(data, ("COGS", "cogs"))
    services = _metric(data, ("services", "Services"))
    if cogs is None:
        return None
    if services is not None and services > 0 and cogs > 0:
        return max(cogs - services, 0.0)
    return cogs


def build_latest_export_payload(user) -> Optional[ExportData]:
    """
    Builds a numeric payload for the most recent financial statement of the user.
    Returns None if there are no statements.
    """

    statements = list(
        FinancialStatement.objects.filter(owner=user).order_by("-year")
    )
    if not statements:
        return None

    latest = statements[0]
    latest_data = latest.data or {}

    revenue = _metric(latest_data, ("Revenue", "revenue"))
    cogs = _cogs_without_services(latest_data)
    gross_margin = _prepare_metric(
        _metric(latest_data, ("GrossMargin", "gross_margin")),
        (revenue - cogs) if revenue is not None and cogs is not None else None,
    )
    overheads = compute_overheads(latest_data)
    depreciation = _metric(latest_data, ("Depreciation", "depreciation"))
    ebit = _prepare_metric(
        _metric(latest_data, ("EBIT", "ebit")),
        (gross_margin or 0.0) - (overheads or 0.0)
        if gross_margin is not None
        else None,
    )
    net_profit = _prepare_metric(
        _metric(latest_data, ("NetProfit", "net_profit")),
        (revenue - cogs - overheads) if revenue is not None and cogs is not None else None,
    )

    prev_statement = statements[1] if len(statements) > 1 else None
    prev_data = prev_statement.data if prev_statement else None
    prev_revenue = _metric(prev_data, ("Revenue", "revenue")) if prev_data else None

    revenue_growth_yoy = growth(revenue, prev_revenue)
    profitability = compute_profitability(revenue, gross_margin, ebit, net_profit)

    revenue_history = []
    for stmt in sorted(statements, key=lambda s: s.year):
        value = _metric((stmt.data or {}), ("Revenue", "revenue"))
        if value is not None:
            revenue_history.append(
                {
                    "year": int(stmt.year),
                    "Revenue": value,
                }
            )

    payload: Dict[str, Any] = {
        "year": int(latest.year),
        "Revenue": revenue,
        "COGS": cogs,
        "GrossMargin": gross_margin,
        "Overheads": overheads,
        "Depreciation": depreciation,
        "EBIT": ebit,
        "NetProfit": net_profit,
        "RevenueGrowthYoY": revenue_growth_yoy,
        "EBITMargin": profitability["op_pct"],
        "NetProfitMargin": profitability["np_pct"],
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
