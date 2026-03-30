"""Business-friendly labels and tooltip text (avoid unexplained jargon)."""
from __future__ import annotations

from taxonomy import CATEGORIES

# Internal category -> display name for charts and UI
CATEGORY_BUSINESS_NAME: dict[str, str] = {
    "Labor / Workforce": "People & field work",
    "Vendor / Third-party": "Vendors & suppliers",
    "Transport / Backhaul": "Backhaul & connectivity",
    "Infrastructure": "Sites & infrastructure",
    "Operations & Maintenance": "Day-to-day operations",
}

METRIC_HELP: dict[str, str] = {
    "total_cost": "Total annual network-related spend included in this analysis (wireless + fiber).",
    "cost_per_site": "Average annual cost for each wireless site in scope — useful for comparing scale and efficiency.",
    "cost_per_tb": "Annual wireless spend divided by data traffic (terabytes). Higher can mean heavier backhaul or less efficient routing.",
    "wireless_fiber_split": "Share of total cost between wireless network and fiber broadband.",
    "vs_peers": "Difference compared with the median of similar operators in the benchmark file.",
    "backhaul_gap": "How much more (or less) of your spend sits in backhaul & connectivity versus peers.",
    "savings_range": "Illustrative savings if typical initiatives succeed — not a guarantee.",
    "effort": "Low = faster to execute; High = more time, stakeholders, or contract changes.",
}


def business_category_name(internal: str) -> str:
    return CATEGORY_BUSINESS_NAME.get(internal, internal)


def top_concentration_phrase(shares: dict[str, float], top_n: int = 2) -> str:
    """Plain English: where most spend sits."""
    items = sorted(shares.items(), key=lambda x: -x[1])[:top_n]
    if len(items) < 2:
        return "Spend is concentrated in a small number of cost areas."
    a, b = items[0][0], items[1][0]
    p0 = items[0][1] * 100
    p1 = items[1][1] * 100
    return (
        f"Most of your spend sits in **{CATEGORY_BUSINESS_NAME.get(a, a)}** and "
        f"**{CATEGORY_BUSINESS_NAME.get(b, b)}** (about **{p0:.0f}%** and **{p1:.0f}%** of the total)."
    )
