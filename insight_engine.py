"""PwC One-style prioritized insights: consultant narrative, traceability, suggested actions."""
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


def _pwc_variance_pack(internal_cat: str, v: float, addr: float, biz: str) -> dict[str, str]:
    """Consultant-grade narrative blocks per taxonomy category."""
    addr_s = _fmt_money(addr)
    common_data = (
        f"Integrated **wireless and fiber** spend rolled into PwC network cost taxonomy; "
        f"variance vs **peer median category share** is **{v:+.0f}%**; addressable base in this category ~**{addr_s}** annualized."
    )
    packs: dict[str, dict[str, str]] = {
        "Transport / Backhaul": {
            "narrative": (
                f"**{biz}** costs appear **elevated relative to similar operators**, often driven by **rural routing complexity** "
                f"and **limited pricing leverage** on dedicated circuits."
            ),
            "why_matters": (
                "Backhaul typically represents a material share of wireless network cost; elevation here directly affects "
                "**cost per unit of traffic** and site-level economics."
            ),
            "data_supports": common_data,
            "suggested_action": (
                "Prioritize **circuit inventory**, **competitive repricing** on top links, and **architecture validation** against traffic growth."
            ),
        },
        "Labor / Workforce": {
            "narrative": (
                f"**{biz}** spend sits **above peer mix**, which frequently reflects **contractor dependence**, **dispatch intensity**, "
                f"or **geographic dispersion** of field work."
            ),
            "why_matters": "Labor is a primary swing factor in **cost per site**; small productivity gains scale across the footprint.",
            "data_supports": common_data,
            "suggested_action": (
                "Tighten **crew productivity** metrics, **scope discipline** on contractors, and **territory design** for installs and maintenance."
            ),
        },
        "Vendor / Third-party": {
            "narrative": (
                f"**{biz}** is **higher than peer benchmarks**, a pattern we often see with **MSOC/OEM fragmentation** or **bespoke scopes** by region."
            ),
            "why_matters": "Vendor spend is highly **addressable** through commercial levers once demand is bundled and specifications harmonized.",
            "data_supports": common_data,
            "suggested_action": (
                "Run **should-cost** views on top categories; **bundle RFPs** and align technical standards before major renewals."
            ),
        },
        "Infrastructure": {
            "narrative": (
                f"**{biz}** costs are **above peer share**, commonly linked to **site count**, **lease escalators**, or **colocation** choices."
            ),
            "why_matters": "Infrastructure drives **fixed cost drag**; rationalization can take time but shifts the long-run cost curve.",
            "data_supports": common_data,
            "suggested_action": (
                "Conduct a **portfolio review**: co-location, **lease renegotiation**, and **decommissioning** of low-value assets."
            ),
        },
        "Operations & Maintenance": {
            "narrative": (
                f"**{biz}** share is **elevated vs peers**, suggesting opportunity in **spares**, **energy**, **dispatch**, or **alarm handling** efficiency."
            ),
            "why_matters": "O&M is recurring spend; **quick wins** here often improve cash without large capital programs.",
            "data_supports": common_data,
            "suggested_action": (
                "Target **automation** in ticketing, **spares policy**, and **energy optimization** on high-load sites."
            ),
        },
    }
    if internal_cat in packs:
        return packs[internal_cat]
    return {
        "narrative": f"**{biz}** is **{v:+.0f}%** vs peer median category share — a **structural mix difference** worth validating with finance and engineering.",
        "why_matters": "Category mix shifts **capital vs opex** exposure and informs where **procurement** and **operations** should focus.",
        "data_supports": common_data,
        "suggested_action": "Deep-dive the **top GL / vendor** drivers behind this category with a cross-functional working team.",
    }


def build_ranked_insights(
    baseline: dict[str, Any],
    variance_df: pd.DataFrame,
    index_info: dict[str, Any],
    dynamic_benchmark: dict[str, Any],
    opportunities: dict[str, Any],
) -> list[dict[str, Any]]:
    """Impact-ordered insight cards with PwC One-style narrative layers."""
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
            pack = _pwc_variance_pack(cat, v, addr, biz)
            cards.append(
                {
                    "id": f"var_{cat}",
                    "title": f"{biz}: peer benchmark gap",
                    "body": pack["narrative"],
                    "narrative": pack["narrative"],
                    "why_matters": pack["why_matters"],
                    "data_supports": pack["data_supports"],
                    "suggested_action": pack["suggested_action"],
                    "variance_pct": v,
                    "impact_score": min(100.0, 40.0 + abs(v) * 2.0 + (addr / max(total, 1.0)) * 40),
                    "severity": "risk" if v > 8 else "watch",
                    "drivers": [
                        "Peer benchmark median category share",
                        "Integrated wireless + fiber taxonomy (PwC network cost model)",
                    ],
                    "data_refs": ["variance_vs_benchmark", "baseline.category_shares"],
                }
            )

    sv = index_info.get("variance_pct_cost_per_site_vs_peer_median")
    if sv is not None and abs(sv) >= 5:
        cards.append(
            {
                "id": "idx_site",
                "title": "Wireless cost intensity (per site)",
                "narrative": (
                    f"Wireless **cost per site** is **{sv:+.1f}%** vs peer median — typically explained by **lease structure**, "
                    f"**vendor/OEM mix**, and **field operating model**."
                ),
                "body": (
                    f"Wireless **cost per site** is **{sv:+.1f}%** vs peer median — typically explained by **lease structure**, "
                    f"**vendor/OEM mix**, and **field operating model**."
                ),
                "why_matters": (
                    "Site-level intensity is a **board-visible** KPI; it anchors discussions on **scale efficiency** and **cost-to-serve**."
                ),
                "data_supports": (
                    "Computed from **rolled-up wireless Amount_USD** and **distinct Site_ID** vs **peer median Cost_per_site_USD** in benchmark file."
                ),
                "suggested_action": (
                    "Commission a **site economics** slice: top quartile sites by cost, lease events in next 24 months, and vendor concentration."
                ),
                "impact_score": 55.0 + min(30.0, abs(sv)),
                "severity": "risk" if sv > 0 else "opportunity",
                "drivers": ["Peer median Cost_per_site_USD", "Site_ID rollup", "Amount_USD (wireless)"],
                "data_refs": ["index_comparison", "wireless_normalized"],
            }
        )

    tv = index_info.get("variance_pct_cost_per_tb_vs_peer_median")
    if tv is not None and abs(tv) >= 6:
        cards.append(
            {
                "id": "idx_tb",
                "title": "Traffic-normalized cost (backhaul signal)",
                "narrative": (
                    f"**Cost per unit of traffic** is **{tv:+.1f}%** vs peer median — a strong signal for **backhaul architecture**, "
                    f"**routing efficiency**, and **circuit commercial terms**."
                ),
                "body": (
                    f"**Cost per unit of traffic** is **{tv:+.1f}%** vs peer median — a strong signal for **backhaul architecture**, "
                    f"**routing efficiency**, and **circuit commercial terms**."
                ),
                "why_matters": (
                    "Traffic-normalized metrics isolate **connectivity economics** from simple site count effects."
                ),
                "data_supports": (
                    "**Traffic_TB_annual** by site (where present) with **wireless spend** vs peer **Cost_per_TB_USD** median."
                ),
                "suggested_action": (
                    "Stress-test **top 10% of sites by $/TB**; align **capacity planning** with **transport sourcing** events."
                ),
                "impact_score": 52.0 + min(28.0, abs(tv)),
                "severity": "risk" if tv > 0 else "opportunity",
                "drivers": ["Traffic_TB_annual", "Transport / backhaul share of spend"],
                "data_refs": ["index_comparison", "baseline.wireless"],
            }
        )

    dyn = (dynamic_benchmark or {}).get("narrative") or ""
    if dyn and dynamic_benchmark.get("variance_pct_site_vs_similar") is not None:
        vsim = dynamic_benchmark["variance_pct_site_vs_similar"]
        cards.append(
            {
                "id": "similar_peers",
                "title": "Similar-peer cohort benchmark",
                "narrative": dyn,
                "body": dyn,
                "why_matters": (
                    "Comparing to **peers with comparable scale and density profile** reduces noise from **one-size-fits-all** averages."
                ),
                "data_supports": (
                    "**Peer clustering** on log cost/site, **operator type**, and **density segment** vs a profile inferred from your wireless/fiber mix."
                ),
                "suggested_action": (
                    "Use this cohort as the **primary benchmark narrative** for executive steering; supplement with **category deep dives**."
                ),
                "impact_score": 48.0 + min(25.0, abs(vsim or 0)),
                "severity": "risk" if (vsim or 0) > 0 else "opportunity",
                "drivers": ["Peer Operator_Type", "Density_Segment", "Cost_per_site_USD"],
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
                "title": "Quantified savings opportunity (modeled)",
                "narrative": (
                    f"Across modeled levers, **quantified savings opportunities** sum to roughly **{_fmt_money(lo)}–{_fmt_money(hi)}** "
                    f"annually — **{ttitle}** leads the prioritized set."
                ),
                "body": (
                    f"Across modeled levers, **quantified savings opportunities** sum to roughly **{_fmt_money(lo)}–{_fmt_money(hi)}** "
                    f"annually — **{ttitle}** leads the prioritized set."
                ),
                "why_matters": (
                    "Leadership needs a **defensible range** tied to **addressable spend** before committing transformation roadmaps."
                ),
                "data_supports": (
                    "**Addressable base** by taxonomy category × **benchmark-informed savings bands** × **feasibility weighting**."
                ),
                "suggested_action": (
                    "Socialize the **range** with finance; pressure-test **top two levers** in a 90-day sprint design."
                ),
                "impact_score": 90.0,
                "severity": "opportunity",
                "drivers": ["Category addressable spend", "Initiative feasibility"],
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
    """Rule-based executive Q&A — PwC One cost intelligence framing."""
    q = question.lower().strip()
    lines: list[str] = []

    if "first" in q or "priorit" in q or "should i do" in q:
        top = (opportunities.get("top_5") or [{}])[0]
        title = top.get("business_title") or top.get("title")
        if title:
            lines.append(
                f"**PwC judgment (illustrative):** start with **{title}** — it ranks highest on **impact × feasibility** in this modeled view. "
                f"Validate scope with your network and procurement leads before formal commitment."
            )

    if any(x in q for x in ("why", "higher", "expensive", "above")) and any(
        y in q for y in ("cost", "spend", "peer")
    ):
        worst = None
        if ranked:
            worst = next((c for c in ranked if c.get("severity") == "risk"), ranked[0])
        if worst:
            lines.append(worst.get("narrative") or worst.get("body", ""))
            if worst.get("why_matters"):
                lines.append(f"**Why it matters:** {worst['why_matters']}")
        sv = index_info.get("variance_pct_cost_per_site_vs_peer_median")
        if sv is not None:
            lines.append(f"**Peer benchmark (wireless cost per site):** **{sv:+.1f}%** vs median.")
        if not variance_df.empty:
            row = variance_df.reindex(variance_df.Variance_pct.abs().sort_values(ascending=False).index).iloc[0]
            if abs(row["Variance_pct"]) >= 4:
                cat = CATEGORY_BUSINESS_NAME.get(str(row["Category"]), row["Category"])
                lines.append(
                    f"**Largest category mix gap:** **{cat}** at **{row['Variance_pct']:+.0f}%** vs peer median share."
                )

    if "savings" in q or "opportunity" in q or "biggest" in q:
        top = (opportunities.get("top_5") or [{}])[0]
        title = top.get("business_title") or top.get("title")
        lo, hi = opportunities.get("total_savings_range", (0, 0))
        if title:
            lines.append(
                f"**Largest quantified opportunity (modeled):** **{title}** — combined initiative range about **{_fmt_money(lo)}–{_fmt_money(hi)}** / year. "
                f"Use **Prioritized action roadmap** for sequencing."
            )

    if "labor" in q or "workforce" in q:
        sh = float((baseline.get("category_shares") or {}).get("Labor / Workforce", 0.0))
        lines.append(f"**People & field work** is **{sh*100:.1f}%** of integrated network spend in this view.")

    if "vendor" in q or "third" in q:
        sh = float((baseline.get("category_shares") or {}).get("Vendor / Third-party", 0.0))
        lines.append(f"**Vendors & suppliers** represent **{sh*100:.1f}%** of integrated network spend.")

    if "backhaul" in q or "transport" in q:
        sh = float((baseline.get("category_shares") or {}).get("Transport / Backhaul", 0.0))
        tv = index_info.get("variance_pct_cost_per_tb_vs_peer_median")
        lines.append(f"**Backhaul & connectivity** is **{sh*100:.1f}%** of spend in this rollup.")
        if tv is not None:
            lines.append(f"**Traffic-normalized cost vs peers:** **{tv:+.1f}%**.")

    if not lines:
        lines.append(
            "Ask, for example: **Why are my costs higher than peers?** · **Where is the biggest savings opportunity?** · "
            "**What should we do first?** — answers draw on your **integrated baseline** and **peer benchmark file** in this workspace."
        )

    return "\n\n".join(lines)
