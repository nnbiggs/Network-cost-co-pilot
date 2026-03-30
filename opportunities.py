"""Map diagnostics to cost levers, savings ranges, and prioritized initiatives."""
from __future__ import annotations

from typing import Any

import pandas as pd

from taxonomy import CATEGORIES

def _effort_label(feasibility: float) -> str:
    """Lower feasibility in our model = harder initiative (higher effort)."""
    if feasibility >= 0.62:
        return "Low"
    if feasibility >= 0.48:
        return "Medium"
    return "High"


LEVERS = [
    {
        "id": "workforce",
        "name": "Workforce optimization",
        "business_title": "Streamline field and contractor work",
        "categories": ["Labor / Workforce"],
        "savings_pct_low": 0.05,
        "savings_pct_high": 0.12,
        "feasibility": 0.65,
        "complexity_note": "Moderate — union/labor rules and contractor mix",
        "complexity_tier": "Medium",
        "time_to_implement": "4–9 months",
        "recommended_action": "Rationalize dispatch territories, tighten contractor scopes, pilot productivity metrics by crew.",
        "pwc_category": "Workforce efficiency",
        "initiative_description": "Align crew productivity, contractor scope, and dispatch design to reduce unit labor cost while protecting service levels.",
    },
    {
        "id": "vendor",
        "name": "Vendor consolidation / renegotiation",
        "business_title": "Optimize vendor contracts",
        "categories": ["Vendor / Third-party"],
        "savings_pct_low": 0.06,
        "savings_pct_high": 0.15,
        "feasibility": 0.55,
        "complexity_note": "Medium-high — OEM lock-in and MSOC transitions",
        "complexity_tier": "High",
        "time_to_implement": "6–18 months",
        "recommended_action": "Run should-cost models on top MSOC/OEM categories; bundle RFPs where volume permits.",
        "pwc_category": "Vendor optimization",
        "initiative_description": "Consolidate vendor relationships and commercial terms where fragmentation drives premium pricing.",
    },
    {
        "id": "transport",
        "name": "Backhaul / transport optimization",
        "business_title": "Reduce backhaul and connectivity cost",
        "categories": ["Transport / Backhaul"],
        "savings_pct_low": 0.05,
        "savings_pct_high": 0.14,
        "feasibility": 0.5,
        "complexity_note": "Medium — routing, fiber vs microwave tradeoffs",
        "complexity_tier": "Medium",
        "time_to_implement": "5–12 months",
        "recommended_action": "Refresh transport topology; benchmark circuit rates; prioritize high-cost rural links.",
        "pwc_category": "Backhaul optimization",
        "initiative_description": "Reduce unit connectivity cost through architecture refresh, circuit repricing, and route rationalization.",
    },
    {
        "id": "infrastructure",
        "name": "Infrastructure rationalization",
        "business_title": "Simplify sites and leases",
        "categories": ["Infrastructure"],
        "savings_pct_low": 0.04,
        "savings_pct_high": 0.10,
        "feasibility": 0.45,
        "complexity_note": "Longer cycle — lease exits and colocation strategy",
        "complexity_tier": "High",
        "time_to_implement": "12–36 months",
        "recommended_action": "Portfolio review: co-locate, decommission low-value sites, renegotiate escalators.",
        "pwc_category": "Infrastructure rationalization",
        "initiative_description": "Simplify the physical footprint and lease structure where site count and colocation economics allow.",
    },
    {
        "id": "netops",
        "name": "Network operations efficiency",
        "business_title": "Run day-to-day network ops leaner",
        "categories": ["Operations & Maintenance"],
        "savings_pct_low": 0.05,
        "savings_pct_high": 0.11,
        "feasibility": 0.7,
        "complexity_note": "Moderate — spares, fuel, dispatch, automation",
        "complexity_tier": "Low",
        "time_to_implement": "3–8 months",
        "recommended_action": "Automate alarms/tickets, tighten spares policy, energy optimization on critical sites.",
        "pwc_category": "Network operations improvement",
        "initiative_description": "Lean out day-to-day O&M through automation, spares discipline, and energy efficiency on critical assets.",
    },
]


def _addressable_by_category(total: float, shares: dict[str, float]) -> dict[str, float]:
    return {c: total * float(shares.get(c, 0.0)) for c in CATEGORIES}


def build_opportunities(
    baseline: dict[str, Any],
    variance_df: pd.DataFrame,
    index_info: dict[str, Any],
) -> dict[str, Any]:
    total = float(baseline["total_network_cost"])
    shares = baseline["category_shares"]
    addr = _addressable_by_category(total, shares)

    var_by_cat = {}
    if not variance_df.empty and "Category" in variance_df.columns:
        var_by_cat = variance_df.set_index("Category")["Variance_pct"].to_dict()

    initiatives = []
    for lever in LEVERS:
        addr_amt = sum(addr.get(c, 0.0) for c in lever["categories"])
        # Boost priority if variance positive (above peer)
        adj = 1.0
        for c in lever["categories"]:
            v = var_by_cat.get(c)
            if v is not None and v > 5:
                adj += 0.08
            if v is not None and v > 12:
                adj += 0.05

        low = addr_amt * lever["savings_pct_low"] * min(adj, 1.25)
        high = addr_amt * lever["savings_pct_high"] * min(adj, 1.25)
        impact = (low + high) / 2.0
        feasibility = lever["feasibility"]
        score = impact * (0.55 + 0.45 * feasibility)
        mid_savings = (low + high) / 2.0
        confidence = int(
            round(
                40
                + 35 * feasibility
                + min(20.0, (mid_savings / max(total, 1.0)) * 120.0)
                + min(10.0, max(0.0, 8.0 - 0.3 * abs(var_by_cat.get(lever["categories"][0], 0.0) or 0.0)))
            )
        )
        confidence = max(38, min(92, confidence))

        initiatives.append(
            {
                "lever_id": lever["id"],
                "title": lever["name"],
                "business_title": lever.get("business_title", lever["name"]),
                "addressable_cost_usd": round(addr_amt, 2),
                "savings_low_usd": round(low, 2),
                "savings_high_usd": round(high, 2),
                "feasibility_0_1": feasibility,
                "effort": _effort_label(feasibility),
                "priority_score": round(score, 2),
                "rationale": lever["complexity_note"],
                "complexity_tier": lever.get("complexity_tier", "Medium"),
                "time_to_implement": lever.get("time_to_implement", "6–12 months"),
                "recommended_action": lever.get("recommended_action", ""),
                "confidence_0_100": confidence,
                "pwc_category": lever.get("pwc_category", "Cost optimization"),
                "initiative_description": lever.get("initiative_description", ""),
                "time_to_value": lever.get("time_to_implement", "6–12 months"),
            }
        )

    # Transport boost if TB variance high
    tbv = index_info.get("variance_pct_cost_per_tb_vs_peer_median")
    if tbv is not None and tbv > 8:
        for ini in initiatives:
            if ini["lever_id"] == "transport":
                ini["savings_low_usd"] = round(ini["savings_low_usd"] * 1.05, 2)
                ini["savings_high_usd"] = round(ini["savings_high_usd"] * 1.08, 2)
                ini["priority_score"] = round(ini["priority_score"] * 1.12, 2)

    initiatives.sort(key=lambda x: x["priority_score"], reverse=True)

    total_low = sum(i["savings_low_usd"] for i in initiatives)
    total_high = sum(i["savings_high_usd"] for i in initiatives)

    top5 = initiatives[:5]
    quick_wins = [i for i in initiatives if i["feasibility_0_1"] >= 0.62][:3]
    longer_term = [i for i in initiatives if i["feasibility_0_1"] < 0.55]

    return {
        "initiatives": initiatives,
        "top_5": top5,
        "quick_wins": quick_wins,
        "longer_term": longer_term,
        "total_savings_range": (total_low, total_high),
    }


def format_roadmap_summary(opps: dict[str, Any]) -> str:
    lo, hi = opps["total_savings_range"]
    lines = [
        f"Estimated combined initiative range: ${lo/1e6:.1f}M–${hi/1e6:.1f}M annualized impact across modeled levers (addressable-base methodology).",
        "Quick wins skew toward network operations and workforce scheduling where feasibility is highest.",
        "Longer-cycle items include infrastructure rationalization and vendor restructuring.",
    ]
    return "\n".join(lines)
