from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from django.db import transaction

from ingest.models import FinancialStatement

from .models import Export


@dataclass
class ExportData:
    payload: Dict[str, Any]
    statement_year: Optional[int]


def _to_number(value: Any) -> Optional[float]:
    """
    Normalizes numeric values that may arrive as strings with spaces or commas.
    Returns None if parsing fails.
    """

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = (
            value.replace("\u00a0", "")
            .replace(" ", "")
            .replace("CZK", "")
            .replace("Kc", "")
            .replace("Kč", "")
            .replace("eur", "")
            .replace("EUR", "")
            .strip()
        )
        cleaned = cleaned.replace(",", ".")
        cleaned = cleaned.rstrip("%")
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _prepare_metric(default_value: Optional[float], fallback: Optional[float] = None) -> Optional[float]:
    return default_value if default_value is not None else fallback


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

    revenue = _to_number(latest_data.get("Revenue"))
    cogs = _to_number(latest_data.get("COGS"))
    gross_margin = _prepare_metric(
        _to_number(latest_data.get("GrossMargin")),
        (revenue - cogs) if revenue is not None and cogs is not None else None,
    )
    overheads = _to_number(latest_data.get("Overheads"))
    depreciation = _to_number(latest_data.get("Depreciation"))
    ebit = _prepare_metric(
        _to_number(latest_data.get("EBIT")),
        (
            (gross_margin or 0.0)
            - (overheads or 0.0)
            - (depreciation or 0.0)
        )
        if gross_margin is not None
        else None,
    )
    net_profit = _to_number(latest_data.get("NetProfit"))

    prev_statement = statements[1] if len(statements) > 1 else None
    prev_data = prev_statement.data if prev_statement else None
    prev_revenue = _to_number(prev_data.get("Revenue")) if prev_data else None

    revenue_growth_yoy = None
    if revenue is not None and prev_revenue not in (None, 0):
        try:
            revenue_growth_yoy = (revenue - prev_revenue) / abs(prev_revenue)
        except Exception:
            revenue_growth_yoy = None

    ebit_margin = None
    if revenue not in (None, 0) and ebit is not None:
        try:
            ebit_margin = ebit / revenue
        except Exception:
            ebit_margin = None

    net_profit_margin = None
    if revenue not in (None, 0) and net_profit is not None:
        try:
            net_profit_margin = net_profit / revenue
        except Exception:
            net_profit_margin = None

    revenue_history = []
    for stmt in sorted(statements, key=lambda s: s.year):
        value = _to_number((stmt.data or {}).get("Revenue"))
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
        "EBITMargin": ebit_margin,
        "NetProfitMargin": net_profit_margin,
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
