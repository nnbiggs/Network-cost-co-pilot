"""Scenario modeling: levers applied to baseline spend → savings and KPI deltas."""
from __future__ import annotations

from typing import Any

from taxonomy import CATEGORIES


def run_scenario(
    baseline: dict[str, Any],
    vendor_cost_reduction_pct: float = 0.0,
    labor_productivity_pct: float = 0.0,
    transport_reduction_pct: float = 0.0,
    infrastructure_reduction_pct: float = 0.0,
    netops_efficiency_pct: float = 0.0,
) -> dict[str, Any]:
    """
    Percent inputs are 0–100 style in UI but passed as fractions e.g. 0.10 for 10%.
    Applies reductions to category buckets (illustrative, additive cap).
    """
    total = float(baseline.get("total_network_cost") or 0.0)
    shares = baseline.get("category_shares") or {}
    w = baseline.get("wireless") or {}
    f = baseline.get("fiber") or {}

    cat_to_lever = {
        "Vendor / Third-party": vendor_cost_reduction_pct,
        "Labor / Workforce": labor_productivity_pct,
        "Transport / Backhaul": transport_reduction_pct,
        "Infrastructure": infrastructure_reduction_pct,
        "Operations & Maintenance": netops_efficiency_pct,
    }

    savings_by_cat: dict[str, float] = {}
    total_savings = 0.0
    for c in CATEGORIES:
        share = float(shares.get(c, 0.0))
        spend = total * share
        pct = float(cat_to_lever.get(c, 0.0))
        sv = spend * min(max(pct, 0.0), 0.5)
        savings_by_cat[c] = sv
        total_savings += sv

    new_total = max(total - total_savings, 0.0)
    w_total = float(w.get("total_cost") or 0.0)
    f_total = float(f.get("total_cost") or 0.0)
    if total > 0:
        w_adj = w_total - total_savings * (w_total / total)
        f_adj = f_total - total_savings * (f_total / total)
    else:
        w_adj, f_adj = w_total, f_total

    n_sites = max(int(w.get("n_sites") or 1), 1)
    tb = max(float(w.get("traffic_tb") or 1.0), 1e-6)
    hp = max(float(f.get("homes_passed") or 0.0), 1.0)

    new_cps = w_adj / n_sites
    new_cpt = w_adj / tb
    new_cphp = f_adj / hp if f_total > 0 else 0.0

    return {
        "total_savings_usd": round(total_savings, 2),
        "savings_by_category": {k: round(v, 2) for k, v in savings_by_cat.items()},
        "new_total_network_cost": round(new_total, 2),
        "kpi_deltas": {
            "cost_per_site": {
                "before": round(w.get("cost_per_site") or 0.0, 2),
                "after": round(new_cps, 2),
            },
            "cost_per_tb": {
                "before": round(w.get("cost_per_tb") or 0.0, 2),
                "after": round(new_cpt, 2),
            },
            "cost_per_home_passed": {
                "before": round(f.get("cost_per_home_passed") or 0.0, 2),
                "after": round(new_cphp, 2),
            },
        },
        "assumptions": (
            "Independent lever application per taxonomy bucket; "
            "wireless/fiber totals scaled pro-rata by pre-scenario share."
        ),
    }
