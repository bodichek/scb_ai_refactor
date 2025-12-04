"""Shared finance helpers used across parsing and dashboards.

All stored monetary values in ``FinancialStatement.income`` / ``balance`` are
expected to be in THOUSANDS (tis. Kč).
Vision parser automatically converts units to thousands.
"""
from typing import Any, Dict, Iterable, Optional

OVERHEAD_COMPONENTS = [
    # Vision parser components (new format)
    "personnel_costs",           # Osobní náklady (agregát)
    "personnel_costs_wages",     # Mzdové náklady
    "personnel_costs_social",    # Náklady na sociální zabezpečení
    "depreciation",              # Odpisy
    "other_operating_expenses",  # Ostatní provozní náklady
    # Legacy components (old parser)
    "services",
    "personnel_wages",
    "personnel_insurance",
    "taxes_fees",
    "other_operating_costs",
    # Title/uppercase variants
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

    For vision parser format:
    - If personnel_costs (aggregate) exists, use it instead of wages + social
    - Include depreciation, other_operating_expenses, cogs_services, taxes_fees
    - CRITICAL: cogs_services goes to overheads (NOT to COGS!)

    For legacy format:
    - Sum all component keys from OVERHEAD_COMPONENTS
    """
    # Check if vision parser format (has personnel_costs aggregate)
    personnel_aggregate = to_number(data.get("personnel_costs"))

    components_sum = 0.0
    counted_keys = set()

    if personnel_aggregate is not None:
        # Vision parser format: use aggregate for personnel
        components_sum += personnel_aggregate
        counted_keys.add("personnel_costs")
        # Skip detailed personnel components to avoid double-counting
        counted_keys.update(["personnel_costs_wages", "personnel_costs_social",
                             "personnel_wages", "personnel_insurance"])

    # CRITICAL: Add cogs_services and taxes_fees to overheads!
    # These are NOT in OVERHEAD_COMPONENTS list but must be included
    cogs_services = to_number(data.get("cogs_services"))
    if cogs_services is not None:
        components_sum += cogs_services
        counted_keys.add("cogs_services")

    taxes_fees = to_number(data.get("taxes_fees"))
    if taxes_fees is not None:
        components_sum += taxes_fees
        counted_keys.add("taxes_fees")

    # Add other components (skip already counted + cogs goods/materials)
    exclude_keys = counted_keys | {"cogs_goods", "cogs_materials"}

    for key in OVERHEAD_COMPONENTS:
        if key in exclude_keys:
            continue
        val = to_number(data.get(key))
        if val is not None:
            components_sum += val

    if components_sum > 0:
        return components_sum

    # Fallback to stored aggregate
    stored = first_number(data, ("Overheads", "overheads"))
    return stored or 0.0


def cogs_without_services(data: Dict[str, Any]) -> Optional[float]:
    """Return COGS with services backed out when both are present."""
    cogs = first_number(data or {}, ("COGS", "cogs"))
    services = first_number(data or {}, ("services", "Services"))
    if cogs is None:
        return None
    if services is not None and services > 0 and cogs > 0:
        return max(cogs - services, 0.0)
    return cogs


def _metric(data: Dict[str, Any], keys: Iterable[str], default: Optional[float] = 0.0) -> Optional[float]:
    val = first_number(data or {}, keys)
    return val if val is not None else default


def _normalize_period(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prefer nested "current" datasets when present (some parsers may include
    current/previous splits). Falls back to the provided mapping.
    """
    if not isinstance(data, dict):
        return {}
    for key in ("current_period", "current", "bezne_obdobi"):
        nested = data.get(key)
        if isinstance(nested, dict):
            return nested
    return data


def compute_metrics(fs) -> Dict[str, Any]:
    """
    Derive core financial metrics from a unified FinancialStatement instance.
    Supports both legacy format and new vision parser component format.
    """
    income_raw = getattr(fs, "income", None) or {}
    balance_raw = getattr(fs, "balance", None) or {}
    income = _normalize_period(income_raw)
    balance = _normalize_period(balance_raw)

    # Revenue: aggregated or from components
    revenue = _metric(income, ("revenue", "Revenue"), None)
    if revenue is None:
        # Vision parser format: compute from components
        rev_products = _metric(income, ("revenue_products_services",), None)
        rev_goods = _metric(income, ("revenue_goods",), None)
        if rev_products is not None or rev_goods is not None:
            revenue = (rev_products or 0.0) + (rev_goods or 0.0)
        else:
            revenue = 0.0

    raw_revenue = revenue

    # COGS: PREFER components over explicit value (to fix parser errors)
    # CRITICAL: COGS = cogs_goods + cogs_materials ONLY (WITHOUT cogs_services!)
    cogs_g = _metric(income, ("cogs_goods",), None)
    cogs_m = _metric(income, ("cogs_materials",), None)
    is_vision_format = False
    has_explicit_cogs = False

    # If components exist, use them (they're more reliable)
    if cogs_g is not None or cogs_m is not None:
        is_vision_format = True
        cogs = (cogs_g or 0.0) + (cogs_m or 0.0)  # WITHOUT cogs_services!
    else:
        # Fall back to explicit cogs value
        cogs = _metric(income, ("cogs", "COGS"), None)
        has_explicit_cogs = cogs is not None
        if cogs is None:
            cogs = 0.0

    # Legacy format only: remove services from COGS if they're counted separately
    # Vision format already includes cogs_services in components above
    # IMPORTANT: Only do this if COGS was NOT explicitly provided
    if not is_vision_format and not has_explicit_cogs:
        services = _metric(income, ("services", "Services"), None)
        if services and cogs > 0:
            cogs = max(cogs - services, 0.0)

    gross_margin = _metric(income, ("gross_margin", "GrossMargin"), None)
    if gross_margin is None:
        gross_margin = revenue - cogs

    overheads = compute_overheads(income)
    depreciation = _metric(income, ("depreciation", "Depreciation"), 0.0) or 0.0

    ebit = _metric(income, ("ebit", "EBIT"), None)
    if ebit is None:
        ebit = gross_margin - overheads

    net_profit = _metric(income, ("net_profit", "NetProfit", "net_income"), None)
    if net_profit is None:
        net_profit = revenue - cogs - overheads

    profitability = compute_profitability(revenue, gross_margin, ebit, net_profit)

    # Extract cogs_materials for display
    cogs_materials = _metric(income, ("cogs_materials",), None) or 0.0

    return {
        "income": income,
        "balance": balance,
        "raw_revenue": raw_revenue,
        "revenue": revenue,
        "cogs": cogs,
        "cogs_materials": cogs_materials,
        "gross_margin": gross_margin,
        "overheads": overheads,
        "depreciation": depreciation,
        "ebit": ebit,
        "net_profit": net_profit,
        "profitability": profitability,
    }


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
