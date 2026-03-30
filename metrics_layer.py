"""Central semantic metrics layer (single definitions for KPIs)."""
from __future__ import annotations

from typing import Any, Callable

# id -> {title, description, unit, compute(baseline, w_kpis, f_kpis, idx) -> float|None}
MetricCompute = Callable[[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]], float | None]


def _cost_per_site(_b: dict[str, Any], w: dict[str, Any], *_: Any) -> float | None:
    v = w.get("cost_per_site")
    return float(v) if v is not None else None


def _cost_per_tb(_b: dict[str, Any], w: dict[str, Any], *_: Any) -> float | None:
    v = w.get("cost_per_tb")
    return float(v) if v is not None else None


def _cost_per_home_passed(_b: dict[str, Any], _w: dict[str, Any], f: dict[str, Any], *_: Any) -> float | None:
    v = f.get("cost_per_home_passed")
    return float(v) if v is not None else None


def _labor_ratio(base: dict[str, Any], *_: Any) -> float | None:
    shares = base.get("category_shares") or {}
    return float(shares.get("Labor / Workforce", 0.0))


def _vendor_ratio(base: dict[str, Any], *_: Any) -> float | None:
    shares = base.get("category_shares") or {}
    return float(shares.get("Vendor / Third-party", 0.0))


def _transport_ratio(base: dict[str, Any], *_: Any) -> float | None:
    shares = base.get("category_shares") or {}
    return float(shares.get("Transport / Backhaul", 0.0))


def _wireless_share(base: dict[str, Any], *_: Any) -> float | None:
    return float(base.get("wireless_share", 0.0))


def _fiber_share(base: dict[str, Any], *_: Any) -> float | None:
    return float(base.get("fiber_share", 0.0))


METRICS: dict[str, dict[str, Any]] = {
    "cost_per_site": {
        "title": "Cost per site (wireless)",
        "description": "Total annual wireless network cost divided by distinct Site_ID count.",
        "unit": "USD",
        "formula": "sum(Amount_USD_wireless) / count_distinct(Site_ID)",
        "compute": _cost_per_site,
    },
    "cost_per_tb": {
        "title": "Cost per TB (wireless)",
        "description": "Wireless cost divided by summed annual traffic (TB) at site level.",
        "unit": "USD",
        "formula": "sum(Amount_USD_wireless) / sum(Traffic_TB_annual per site)",
        "compute": _cost_per_tb,
    },
    "cost_per_home_passed": {
        "title": "Cost per home passed (fiber)",
        "description": "Total fiber-attributed spend divided by homes passed.",
        "unit": "USD",
        "formula": "sum(fiber cost stack) / sum(Homes_Passed)",
        "compute": _cost_per_home_passed,
    },
    "labor_ratio": {
        "title": "Labor share of network cost",
        "description": "Share of combined wireless + fiber spend mapped to Labor / Workforce.",
        "unit": "ratio",
        "formula": "Labor_spend / total_network_cost",
        "compute": _labor_ratio,
    },
    "vendor_ratio": {
        "title": "Vendor / third-party share",
        "description": "Share of network spend in Vendor / Third-party taxonomy category.",
        "unit": "ratio",
        "formula": "Vendor_spend / total_network_cost",
        "compute": _vendor_ratio,
    },
    "transport_ratio": {
        "title": "Transport / backhaul share",
        "description": "Share of network spend in Transport / Backhaul.",
        "unit": "ratio",
        "formula": "Transport_spend / total_network_cost",
        "compute": _transport_ratio,
    },
    "wireless_share": {
        "title": "Wireless share of total",
        "description": "Wireless spend as a fraction of wireless + fiber total.",
        "unit": "ratio",
        "formula": "wireless_total / (wireless_total + fiber_total)",
        "compute": _wireless_share,
    },
    "fiber_share": {
        "title": "Fiber share of total",
        "description": "Fiber spend as a fraction of wireless + fiber total.",
        "unit": "ratio",
        "formula": "fiber_total / (wireless_total + fiber_total)",
        "compute": _fiber_share,
    },
}


def compute_all_metrics(
    baseline: dict[str, Any],
    index_comparison: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return metric_id -> {value, meta}."""
    w = baseline.get("wireless") or {}
    f = baseline.get("fiber") or {}
    out: dict[str, dict[str, Any]] = {}
    for mid, meta in METRICS.items():
        fn = meta["compute"]
        val = fn(baseline, w, f, index_comparison)
        out[mid] = {
            "value": val,
            "title": meta["title"],
            "description": meta["description"],
            "unit": meta["unit"],
            "formula": meta["formula"],
        }
    return out
