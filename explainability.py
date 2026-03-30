"""Transparency payloads for insights and recommendations."""
from __future__ import annotations

from typing import Any

import pandas as pd


def explain_variance_row(variance_df: pd.DataFrame, category: str) -> dict[str, Any]:
    """Why this category variance line exists."""
    if variance_df.empty or "Category" not in variance_df.columns:
        return {"summary": "No variance table.", "steps": []}
    row = variance_df[variance_df["Category"] == category]
    if row.empty:
        return {"summary": f"Category {category!r} not found.", "steps": []}
    r = row.iloc[0]
    obs = r.get("Observed_share")
    bench = r.get("Benchmark_median_share")
    vp = r.get("Variance_pct")
    steps = [
        "1. Roll up your wireless line items and fiber wide columns into the standard taxonomy.",
        "2. Compute each category’s share of total network cost.",
        "3. Take peer **median** share per category from the benchmark file (excluding 'Your Network' rows).",
        f"4. Variance % = (your share − peer median share) / peer median share × 100 → **{vp:+.1f}%** for **{category}**.",
    ]
    return {
        "summary": (
            f"Your observed share is **{float(obs)*100:.1f}%** vs peer median **{float(bench)*100:.1f}%** "
            f"(where benchmark data exists)."
        ),
        "steps": steps,
        "inputs": {"Observed_share": obs, "Benchmark_median_share": bench, "Variance_pct": vp},
    }


def explain_index_comparison(index_info: dict[str, Any], metric: str = "site") -> dict[str, Any]:
    """site | tb"""
    if metric == "tb":
        key_med = "benchmark_median_cost_per_tb_usd"
        label = "cost per TB (USD)"
    else:
        key_med = "benchmark_median_cost_per_site_usd"
        label = "cost per site (USD)"
    med = index_info.get(key_med)
    var_key = (
        "variance_pct_cost_per_site_vs_peer_median"
        if metric != "tb"
        else "variance_pct_cost_per_tb_vs_peer_median"
    )
    v = index_info.get(var_key)
    if v is not None:
        summ = f"Compared **your** {label} to the **peer median** from the benchmark extract; variance **{v:+.1f}%**."
    else:
        summ = f"Peer median {label}: **{med}** (variance not computed if peers missing)."
    return {
        "summary": summ,
        "steps": [
            "1. Sum wireless Amount_USD and divide by distinct Site_ID (or traffic TB) for your KPI.",
            "2. Peer median uses Cost_per_site_USD / Cost_per_TB_USD from benchmark peers (deduped by Peer_Operator).",
            f"3. Variance vs median: **{v:+.1f}%**." if v is not None else "3. Variance not computed (missing peer USD columns).",
        ],
        "inputs": {key_med: med, var_key: v},
    }


def explain_opportunity(initiative: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Map recommendation to data lineage."""
    total = float(baseline.get("total_network_cost") or 0.0)
    return {
        "summary": initiative.get("rationale") or initiative.get("business_title") or "",
        "steps": [
            "1. Identify taxonomy categories attached to this lever (e.g., Vendor / Third-party).",
            "2. Addressable base = category spend × total network cost (**$"
            + _usd(total)
            + "** total).",
            "3. Apply savings % band × feasibility weight to produce low/high range.",
            f"4. **Confidence {initiative.get('confidence_0_100', '—')}/100** reflects data completeness and lever history (heuristic); **PwC judgment** calibrates for client context.",
        ],
        "inputs": {
            "addressable_cost_usd": initiative.get("addressable_cost_usd"),
            "savings_low_usd": initiative.get("savings_low_usd"),
            "savings_high_usd": initiative.get("savings_high_usd"),
        },
    }


def _usd(n: float) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return f"{n:,.0f}"
