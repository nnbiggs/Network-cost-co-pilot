"""LLM-assisted narrative insights from baseline and benchmark outputs."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

def _openai_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _format_currency(n: float) -> str:
    if n >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n/1_000:.0f}K"
    return f"${n:,.0f}"


def rule_based_insights(
    baseline: dict[str, Any],
    variance_df: Any,
    index_info: dict[str, Any],
    opportunities_summary: Optional[dict[str, Any]] = None,
) -> str:
    """Plain-English summary when no LLM is configured."""
    w = baseline["wireless"]
    f = baseline["fiber"]
    lines = [
        "Based on benchmark data and observed cost patterns, the integrated network shows a clear cost profile across wireless and fiber assets.",
        f"Wireless cost intensity is approximately {_format_currency(w['cost_per_site'])} per site, compared with a peer median of "
        f"{_format_currency(index_info.get('benchmark_median_cost_per_site_usd') or 0)} where available.",
        f"Traffic-normalized wireless spend is about {_format_currency(w['cost_per_tb'])} per TB of annual traffic.",
    ]
    if f["homes_passed"]:
        lines.append(
            f"Fiber-related spend implies roughly {_format_currency(f['cost_per_home_passed'])} per home passed and "
            f"{_format_currency(f['cost_per_home_connected'])} per connected home, with build-oriented costs representing "
            f"{f['build_share']*100:.0f}% of the fiber cost stack in this view."
        )

    # Top variance categories
    if hasattr(variance_df, "sort_values"):
        worst = variance_df.reindex(variance_df.Variance_pct.abs().sort_values(ascending=False).index).head(3)
        for _, row in worst.iterrows():
            if abs(row["Variance_pct"]) < 3:
                continue
            lines.append(
                f"{row['Category']} represents a higher share of network cost than the peer median by about "
                f"{row['Variance_pct']:+.1f} percentage points — a focal area for efficiency review."
            )

    sv = index_info.get("variance_pct_cost_per_site_vs_peer_median")
    tv = index_info.get("variance_pct_cost_per_tb_vs_peer_median")
    if sv is not None:
        lines.append(
            f"Site-level costs run about {sv:+.1f}% versus the peer median on a comparable basis, suggesting "
            "lease, vendor, and field-operations mix as primary swing factors."
        )
    if tv is not None and abs(tv) > 5:
        lines.append(
            f"Backhaul- and traffic-normalized costs appear roughly {tv:+.1f}% versus peers, consistent with transport "
            "complexity and contract structure in mixed-density markets."
        )

    if opportunities_summary and opportunities_summary.get("total_savings_range"):
        lo, hi = opportunities_summary["total_savings_range"]
        lines.append(
            f"Structured initiatives across workforce, vendor, and transport levers point to an estimated "
            f"{_format_currency(lo)}–{_format_currency(hi)} annual opportunity under typical execution assumptions."
        )

    return "\n\n".join(lines)


def generate_insights_llm(
    baseline: dict[str, Any],
    variance_df: Any,
    index_info: dict[str, Any],
    opportunities_summary: Optional[dict[str, Any]] = None,
    model: Optional[str] = None,
) -> str:
    if not _openai_available():
        return rule_based_insights(baseline, variance_df, index_info, opportunities_summary)

    from openai import OpenAI

    client = OpenAI()
    m = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    payload = {
        "totals": {
            "total_network_cost": baseline["total_network_cost"],
            "wireless_share": baseline["wireless_share"],
            "fiber_share": baseline["fiber_share"],
        },
        "wireless_kpis": baseline["wireless"],
        "fiber_kpis": baseline["fiber"],
        "category_variance_pct_vs_peer_median": variance_df.to_dict(orient="records") if hasattr(variance_df, "to_dict") else [],
        "index_comparison": index_info,
        "opportunity_headline": opportunities_summary or {},
    }

    prompt = (
        "You are a telecom network cost diagnostic assistant for an integrated regional operator (wireless + fiber).\n"
        "Write 4–6 short paragraphs of executive-ready findings. Do not say the data is synthetic or simulated.\n"
        "Frame conclusions as: 'Based on benchmark data and observed cost patterns…'\n"
        "Call out: (1) site and traffic-normalized wireless costs vs peers, (2) fiber cost-per-passed/connected and build vs run, "
        "(3) top category gaps vs benchmark, (4) plausible drivers (vendor scale, rural cost-to-serve, backhaul, fragmentation), "
        "(5) savings magnitude if provided.\n"
        f"Structured context JSON:\n{json.dumps(payload, default=str)[:12000]}"
    )

    resp = client.chat.completions.create(
        model=m,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35,
        max_tokens=900,
    )
    return (resp.choices[0].message.content or "").strip()


def generate_insights(
    baseline: dict[str, Any],
    variance_df: Any,
    index_info: dict[str, Any],
    opportunities_summary: Optional[dict[str, Any]] = None,
) -> str:
    """Prefer LLM when API key is set; otherwise deterministic narrative."""
    if _openai_available():
        try:
            return generate_insights_llm(baseline, variance_df, index_info, opportunities_summary)
        except Exception:
            return rule_based_insights(baseline, variance_df, index_info, opportunities_summary)
    return rule_based_insights(baseline, variance_df, index_info, opportunities_summary)
