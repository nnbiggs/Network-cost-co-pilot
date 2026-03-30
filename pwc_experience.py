"""
PwC One — Network Cost Intelligence: positioning copy, demo storyline, and executive payloads.

Live demo talk track is also documented in README.md at the repository root.
"""
from __future__ import annotations

from typing import Any

from filters import NETWORK_FIBER

# -----------------------------------------------------------------------------
# Positioning (use across UI; avoid "dashboard only" / "prototype" framing)
# -----------------------------------------------------------------------------

PRODUCT_TITLE = "PwC One — Network Cost Intelligence"
PRODUCT_SUBTITLE = "A PwC One-powered decision experience for telecom network cost optimization"
VALUE_PROPOSITION = (
    "Transform fragmented wireless, fiber, and benchmark data into an **integrated cost baseline**, "
    "**peer benchmark comparison**, **AI-assisted cost intelligence**, and a **prioritized action roadmap** — "
    "with **PwC judgment** applied to validate and translate findings into execution."
)

STORYLINE_COMPRESSION = (
    "**This is how PwC One compresses a traditional diagnostic:** faster ingestion, smarter benchmarking, clearer actions — "
    "from data to decision to execution in one secure analytical workspace."
)

TRUST_STRIP = (
    "**AI accelerates analysis; PwC judgment validates.** Insights are traceable to your data and benchmark logic; "
    "recommendations are structured for steering-committee discussion, not generic automation."
)

SECURE_WORKSPACE_NOTE = (
    "Client data is processed in your session for this experience — design intent aligns with a **secure client workspace** "
    "in a full PwC One deployment."
)

DEMO_PHASES = [
    "Ingest fragmented cost data",
    "Standardize to a common cost taxonomy",
    "Build the integrated cost baseline",
    "Benchmark against relevant peers (including similar-peer cohorts)",
    "Surface AI-assisted drivers of cost gaps",
    "Translate into quantified savings opportunities and a prioritized roadmap",
]


def build_executive_panel(
    result: dict[str, Any],
    network: str,
) -> dict[str, Any]:
    """Structured metrics for landing / overview cards."""
    idx = result["index_comparison"]
    opps = result["opportunities"]
    dyn = result.get("dynamic_peer_benchmark") or {}
    dh = result.get("data_health") or {}

    site_v = idx.get("variance_pct_cost_per_site_vs_peer_median")
    vsim = dyn.get("variance_pct_site_vs_similar")
    lo, hi = opps.get("total_savings_range", (0, 0))
    top = (opps.get("top_5") or [{}])[0]
    top_title = top.get("business_title") or top.get("title") or "Prioritized initiatives"

    gap_line = "Peer benchmark comparison loaded — open **Peer benchmark comparison** for wireless KPIs."
    if network != NETWORK_FIBER and site_v is not None:
        if site_v > 3:
            gap_line = f"**Cost gap (wireless):** approximately **{site_v:+.0f}%** vs peer median on **cost per site** — structural efficiency and vendor/lease mix are primary hypotheses."
        elif site_v < -3:
            gap_line = f"**Cost position (wireless):** approximately **{abs(site_v):.0f}% below** peer median on **cost per site** — favorable vs benchmark; still scan opportunities by category."
        else:
            gap_line = f"**Cost per site (wireless)** is **aligned** with peer median (~**{site_v:+.1f}%**); category mix and traffic-normalized metrics still matter."

    if network != NETWORK_FIBER and vsim is not None and abs(vsim) >= 3:
        gap_line += f" Against **similar-peer clustering**, cost per site is **{vsim:+.0f}%** — a tailored cohort, not a single industry average."

    priority_actions = []
    for ini in (opps.get("top_5") or [])[:3]:
        priority_actions.append(
            {
                "title": ini.get("business_title") or ini.get("title"),
                "savings": f"${ini.get('savings_low_usd', 0)/1e6:.2f}M–${ini.get('savings_high_usd', 0)/1e6:.2f}M / yr (modeled)"
                if ini.get("savings_high_usd", 0) >= 1_000_000
                else f"${ini.get('savings_low_usd', 0)/1e3:.0f}K–${ini.get('savings_high_usd', 0)/1e3:.0f}K / yr (modeled)",
            }
        )

    return {
        "cost_gap_summary": gap_line,
        "top_optimization_lever": top_title,
        "estimated_savings_range": (lo, hi),
        "priority_actions": priority_actions,
        "data_health_score": dh.get("data_health_score"),
        "mapping_confidence": dh.get("mapping_confidence_0_100"),
    }


def phase_headline(phase_key: str) -> str:
    """One-line executive context per guided phase."""
    return {
        "overview": "**Executive overview** — how PwC One moves from fragmented data to quantified opportunities.",
        "ingest": "**Ingest & standardize** — AI-assisted field alignment into a common network cost taxonomy.",
        "baseline": "**Integrated cost baseline** — where spend sits across wireless, fiber, and cost categories.",
        "benchmark": "**Peer benchmark comparison** — where you stand vs peers and similar operators.",
        "insights": "**AI-assisted gap insights** — consultant-style drivers with traceable evidence.",
        "roadmap": "**Prioritized action roadmap** — quantified opportunities, sequencing, and steering-ready output.",
    }.get(phase_key, "")
