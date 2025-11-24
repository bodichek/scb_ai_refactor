"""Shared finance helpers used across parsing and dashboards.

All stored monetary values in ``FinancialStatement.data`` are expected to be
absolute CZK amounts (no thousands scaling).
"""
from typing import Any, Dict, Iterable, Optional

OVERHEAD_COMPONENTS = [
    # detailed components (lowercase)
    "services",
    "personnel_wages",
    "personnel_insurance",
    "taxes_fees",
    "depreciation",
    "other_operating_costs",
    # possible variants from other parsers (Title/uppercase)
    "Services",
    "PersonnelWages",
    "PersonnelInsurance",
    "TaxesFees",
    "Depreciation",
    "OtherOperatingCosts",
]


def to_number(value: Any) -> Optional[float]:
    """Normalize numeric values that may be strings with currency/spacing."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return None
    if isinstance(value, str):
        cleaned = (
            value.replace("\u00a0", "")
            .replace(" ", "")
            .replace("CZK", "")
            .replace("Kc", "")
            .replace("K\u010d", "")
            .replace("eur", "")
            .replace("EUR", "")
            .rstrip("%")
            .strip()
        )
        if not cleaned:
            return None

        has_comma = "," in cleaned
        has_dot = "." in cleaned
        if has_comma and has_dot:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif has_comma:
            cleaned = cleaned.replace(",", ".")

        try:
            return float(cleaned)
        except Exception:
            return None
    return None


def first_number(data: Dict[str, Any], keys: Iterable[str]) -> Optional[float]:
    """Return the first parseable numeric value from the provided keys."""
    for key in keys:
        val = to_number(data.get(key))
        if val is not None:
            return val
    return None


def compute_overheads(data: Dict[str, Any]) -> float:
    """
    Sum overheads from detailed components; fall back to stored total only
    when no components are available.
    """
    components_sum = 0.0
    for key in OVERHEAD_COMPONENTS:
        val = to_number(data.get(key))
        if val is not None:
            components_sum += val

    if components_sum > 0:
        return components_sum

    stored = first_number(data, ("Overheads", "overheads"))
    return stored or 0.0


def compute_profitability(
    revenue: Any, gross_margin: Any, ebit: Any, net_profit: Any
) -> Dict[str, float]:
    revenue_val = to_number(revenue)
    gm_val = to_number(gross_margin)
    ebit_val = to_number(ebit)
    np_val = to_number(net_profit)

    if not revenue_val:
        return {"gm_pct": 0.0, "op_pct": 0.0, "np_pct": 0.0}

    return {
        "gm_pct": (gm_val or 0.0) / revenue_val * 100.0,
        "op_pct": (ebit_val or 0.0) / revenue_val * 100.0,
        "np_pct": (np_val or 0.0) / revenue_val * 100.0,
    }


def growth(current: Any, previous: Any) -> Optional[float]:
    """Compute YoY growth in %, returning None when previous is 0/None."""
    prev_val = to_number(previous)
    curr_val = to_number(current)
    if prev_val in (None, 0):
        return None
    try:
        return (curr_val - prev_val) / abs(prev_val) * 100.0
    except Exception:
        return None
