"""Ranked insights, root-cause style drivers, and lightweight NL answers."""
from __future__ import annotations

from typing import Any

import pandas as pd

from ui_copy import CATEGORY_BUSINESS_NAME


def _fmt_money(n: float) -> str:
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"${n/1_000:.0f}K"
    return f"${n:,.0f}"


def build_ranked_insights(
    baseline: dict[str, Any],
    variance_df: pd.DataFrame,
    index_info: dict[str, Any],
    dynamic_benchmark: dict[str, Any],
    opportunities: dict[str, Any],
) -> list[dict[str, Any]]:
    """Impact-ordered cards with title, body, severity, drivers."""
    cards: list[dict[str, Any]] = []
    total = float(baseline.get("total_network_cost") or 0.0)
    shares = baseline.get("category_shares") or {}

    if not variance_df.empty and "Variance_pct" in variance_df.columns:
        for _, row in variance_df.sort_values("Variance_pct", ascending=False).iterrows():
            cat = str(row["Category"])
            v = float(row["Variance_pct"])
            if v < 4:
                continue
            addr = total * float(shares.get(cat, 0.0))
            biz = CATEGORY_BUSINESS_NAME.get(cat, cat)
            cards.append(
                {
                    "id": f"var_{cat}",
                    "title": f"{biz} above peer mix",
                    "body": (
                        f"**{biz}** is about **{v:+.0f}%** vs peer median share — roughly **{_fmt_money(addr)}** "
                        f"in annual spend in this category (addressable base for initiatives)."
                    ),
                    "impact_score": min(100.0, 40.0 + abs(v) * 2.0 + (addr / max(total, 1.0)) * 40),
                    "severity": "risk" if v > 8 else "watch",
                    "drivers": [
                        "Peer benchmark median category share",
                        "Your rolled-up wireless + fiber taxonomy mapping",
                    ],
                    "data_refs": ["variance_vs_benchmark", "baseline.category_shares"],
                }
            )

    sv = index_info.get("variance_pct_cost_per_site_vs_peer_median")
    if sv is not None and abs(sv) >= 5:
        cards.append(
            {
                "id": "idx_site",
                "title": "Wireless cost per site vs peers",
                "body": f"Cost per site is **{sv:+.1f}%** vs **peer median** — lease, vendor, and field mix are typical levers.",
                "impact_score": 55.0 + min(30.0, abs(sv)),
                "severity": "risk" if sv > 0 else "opportunity",
                "drivers": ["Peer median Cost_per_site_USD", "Your Site_ID rollup and Amount_USD"],
                "data_refs": ["index_comparison", "wireless_normalized"],
            }
        )

    tv = index_info.get("variance_pct_cost_per_tb_vs_peer_median")
    if tv is not None and abs(tv) >= 6:
        cards.append(
            {
                "id": "idx_tb",
                "title": "Traffic-normalized wireless cost",
                "body": f"Cost per TB is **{tv:+.1f}%** vs peer median — often driven by **backhaul** architecture and **routing** efficiency.",
                "impact_score": 52.0 + min(28.0, abs(tv)),
                "severity": "risk" if tv > 0 else "opportunity",
                "drivers": ["Traffic_TB_annual by site", "Transport share of spend"],
                "data_refs": ["index_comparison", "baseline.wireless"],
            }
        )

    dyn = (dynamic_benchmark or {}).get("narrative") or ""
    if dyn and dynamic_benchmark.get("variance_pct_site_vs_similar") is not None:
        vsim = dynamic_benchmark["variance_pct_site_vs_similar"]
        cards.append(
            {
                "id": "similar_peers",
                "title": "Similar-peer cohort (dynamic benchmark)",
                "body": dyn,
                "impact_score": 48.0 + min(25.0, abs(vsim or 0)),
                "severity": "risk" if (vsim or 0) > 0 else "opportunity",
                "drivers": [
                    "Peer Operator_Type and Density_Segment",
                    "Cost scale proximity in log space",
                ],
                "data_refs": ["benchmarks", "dynamic_peer_benchmark"],
            }
        )

    lo, hi = opportunities.get("total_savings_range", (0, 0))
    if hi and hi > 0:
        top = (opportunities.get("top_5") or [{}])[0]
        ttitle = top.get("business_title") or top.get("title") or "Top initiative"
        cards.append(
            {
                "id": "savings_headline",
                "title": "Largest modeled savings lever",
                "body": f"**{ttitle}** — combined modeled initiative range **{_fmt_money(lo)}–{_fmt_money(hi)}** / yr (illustrative).",
                "impact_score": 90.0,
                "severity": "opportunity",
                "drivers": ["Category addressable spend", "Lever feasibility weighting"],
                "data_refs": ["opportunities.initiatives"],
            }
        )

    cards.sort(key=lambda c: c["impact_score"], reverse=True)
    return cards


def answer_question(
    question: str,
    baseline: dict[str, Any],
    variance_df: pd.DataFrame,
    index_info: dict[str, Any],
    opportunities: dict[str, Any],
    ranked: list[dict[str, Any]],
) -> str:
    """Rule-based answers for common executive questions (no external LLM required)."""
    q = question.lower().strip()
    w = baseline.get("wireless") or {}
    lines: list[str] = []

    if any(x in q for x in ("why", "higher", "expensive", "above")) and any(
        y in q for y in ("cost", "spend", "peer")
    ):
        worst = None
        if ranked:
            worst = next((c for c in ranked if c.get("severity") == "risk"), ranked[0])
        if worst:
            lines.append(worst.get("body", ""))
        sv = index_info.get("variance_pct_cost_per_site_vs_peer_median")
        if sv is not None:
            lines.append(f"Wireless **cost per site** is **{sv:+.1f}%** vs peer median.")
        if not variance_df.empty:
            row = variance_df.reindex(variance_df.Variance_pct.abs().sort_values(ascending=False).index).iloc[0]
            if abs(row["Variance_pct"]) >= 4:
                cat = CATEGORY_BUSINESS_NAME.get(str(row["Category"]), row["Category"])
                lines.append(
                    f"Largest **category mix gap**: **{cat}** at **{row['Variance_pct']:+.0f}%** vs peer median share."
                )

    if "savings" in q or "opportunity" in q or "biggest" in q:
        top = (opportunities.get("top_5") or [{}])[0]
        title = top.get("business_title") or top.get("title")
        lo, hi = opportunities.get("total_savings_range", (0, 0))
        if title:
            lines.append(
                f"Biggest modeled opportunity: **{title}** — estimated **{_fmt_money(lo)}–{_fmt_money(hi)}** / year across all levers."
            )

    if "labor" in q or "workforce" in q:
        sh = float((baseline.get("category_shares") or {}).get("Labor / Workforce", 0.0))
        lines.append(f"Labor / workforce is **{sh*100:.1f}%** of total network spend in this view.")

    if "vendor" in q or "third" in q:
        sh = float((baseline.get("category_shares") or {}).get("Vendor / Third-party", 0.0))
        lines.append(f"Vendor / third-party is **{sh*100:.1f}%** of total network spend.")

    if "backhaul" in q or "transport" in q:
        sh = float((baseline.get("category_shares") or {}).get("Transport / Backhaul", 0.0))
        tv = index_info.get("variance_pct_cost_per_tb_vs_peer_median")
        lines.append(f"Transport / backhaul share is **{sh*100:.1f}%** of spend.")
        if tv is not None:
            lines.append(f"Cost **per TB** vs peers: **{tv:+.1f}%**.")

    if not lines:
        lines.append(
            "Try asking: **Why are my costs higher than peers?**, **Where is the biggest savings opportunity?**, "
            "or **How does backhaul compare?** — I answer from your loaded benchmark and cost tables."
        )

    return "\n\n".join(lines)
