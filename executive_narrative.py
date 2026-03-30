"""Short, plain-English lines for executives (1–2 sentences, action-oriented)."""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from ui_copy import CATEGORY_BUSINESS_NAME


def _usd_short(n: float) -> str:
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"${n/1_000:.0f}K"
    return f"${n:,.0f}"


def benchmark_plain_insight(
    variance_df: pd.DataFrame,
    index_info: dict[str, Any],
) -> str:
    """One sentence on the biggest gap vs peers."""
    site_v = index_info.get("variance_pct_cost_per_site_vs_peer_median")
    tb_v = index_info.get("variance_pct_cost_per_tb_vs_peer_median")

    worst_cat = None
    worst_val = 0.0
    if variance_df is not None and not variance_df.empty and "Category" in variance_df.columns:
        sub = variance_df.copy()
        sub["absv"] = sub["Variance_pct"].abs()
        row = sub.sort_values("absv", ascending=False).iloc[0]
        worst_cat = str(row["Category"])
        worst_val = float(row["Variance_pct"])

    if worst_cat == "Transport / Backhaul" and worst_val > 8:
        return (
            f"**Backhaul & connectivity** appears **~{worst_val:.0f}% above peer mix** — a pattern we often associate with **rural routing complexity** "
            f"and **limited pricing leverage** on dedicated circuits."
        )
    if worst_cat and worst_val > 10:
        name = CATEGORY_BUSINESS_NAME.get(worst_cat, worst_cat)
        return (
            f"**{name}** stands **materially above peer benchmark mix** (~**{worst_val:+.0f}%**) — warrants a **focused diagnostic** with network and finance."
        )

    if site_v is not None and abs(site_v) >= 5:
        direction = "higher" if site_v > 0 else "lower"
        return (
            f"Wireless **cost per site** is about **{abs(site_v):.0f}% {direction}** than **peer median** — **vendor/OEM**, **leases**, and **field operating model** "
            f"typically explain the gap."
        )

    if tb_v is not None and abs(tb_v) >= 8:
        direction = "higher" if tb_v > 0 else "lower"
        return (
            f"**Traffic-normalized** wireless cost is **{direction}** peers by ~**{abs(tb_v):.0f}%** — consistent with **backhaul architecture**, **routing**, and **circuit economics**."
        )

    return (
        "Overall, the **integrated baseline** sits **near peer norms** on headline metrics — still review **quantified savings opportunities** "
        "and **category mix** for execution upside."
    )


def executive_summary_lines(
    baseline: dict[str, Any],
    index_info: dict[str, Any],
    opps: dict[str, Any],
) -> dict[str, str]:
    """Headline strings for the summary strip."""
    site_v = index_info.get("variance_pct_cost_per_site_vs_peer_median")
    lo, hi = opps.get("total_savings_range", (0, 0))
    top = (opps.get("top_5") or [{}])[0]
    top_title = top.get("business_title") or top.get("title") or "Cost initiatives"

    if site_v is None:
        peer_line = "Peer comparison: benchmark data loaded — see the Comparison step."
    elif site_v > 3:
        peer_line = f"You are spending about **{site_v:.0f}% more per site** than the peer median (wireless)."
    elif site_v < -3:
        peer_line = f"You are spending about **{abs(site_v):.0f}% less per site** than the peer median (wireless)."
    else:
        peer_line = "Your **cost per site** is **in line** with the peer median (wireless)."

    savings_line = f"**Quantified savings opportunities (modeled):** **{_usd_short(lo)}–{_usd_short(hi)}** per year — for steering discussion with finance."
    top_line = f"**Lead optimization lever:** **{top_title}**."

    return {
        "peer": peer_line,
        "savings": savings_line,
        "top": top_line,
    }


def executive_story_mode(
    baseline: dict[str, Any],
    index_info: dict[str, Any],
    opps: dict[str, Any],
    ranked_insights: list[dict[str, Any]],
    dynamic_benchmark: dict[str, Any],
    data_health: dict[str, Any],
) -> dict[str, Any]:
    """Slide-ready: 3 findings, 3 opportunities, savings, health."""
    findings: list[str] = []
    for card in (ranked_insights or [])[:3]:
        if card.get("title") and card.get("body"):
            findings.append(f"**{card['title']}** — {card['body']}")

    if len(findings) < 3:
        site_v = index_info.get("variance_pct_cost_per_site_vs_peer_median")
        if site_v is not None:
            findings.append(f"Wireless **cost per site** vs peer median: **{site_v:+.1f}%**.")
        dyn = (dynamic_benchmark or {}).get("narrative")
        if dyn:
            findings.append(dyn)
        while len(findings) < 3:
            findings.append("Continue refining category mapping and peer file coverage to sharpen comparisons.")

    op_rows = opps.get("top_5") or []
    opportunities_lines: list[str] = []
    for ini in op_rows[:3]:
        title = ini.get("business_title") or ini.get("title")
        sl = ini.get("savings_low_usd", 0)
        sh = ini.get("savings_high_usd", 0)
        conf = ini.get("confidence_0_100", "—")
        opportunities_lines.append(
            f"**{title}** — {_usd_short(sl)}–{_usd_short(sh)}/yr (confidence **{conf}/100**)"
        )

    lo, hi = opps.get("total_savings_range", (0, 0))
    score = data_health.get("data_health_score", "—")

    return {
        "title": "PwC One — Network Cost Intelligence · executive summary",
        "findings": findings[:3],
        "opportunities": opportunities_lines[:3],
        "estimated_savings": f"{_usd_short(lo)} – {_usd_short(hi)} per year — **quantified savings opportunities** (modeled; PwC validates with client).",
        "data_health": f"**Data quality & coverage:** **{score}/100** ({data_health.get('data_health_band', '')})",
        "footer": "Visual logic: **above peer** = cost pressure vs benchmark; **below peer** = favorable. **AI-assisted** analysis with **PwC judgment**.",
    }
