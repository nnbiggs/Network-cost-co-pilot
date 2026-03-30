"""End-to-end analysis: ingest → normalize → baseline → benchmark → opportunities."""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

import ingestion
import normalization
from baseline import combined_baseline, compute_fiber_kpis, compute_wireless_kpis
from benchmarking import (
    dynamic_peer_benchmark,
    index_comparison,
    segment_highlights,
    variance_vs_benchmark,
)
from data_health import compute_data_health
from insight_engine import build_ranked_insights
from insights import generate_insights
from metrics_layer import compute_all_metrics
from opportunities import build_opportunities


def analyze_dataframes(
    w_raw: pd.DataFrame,
    f_raw: pd.DataFrame,
    b_raw: pd.DataFrame,
    source_label: Optional[str] = None,
) -> dict[str, Any]:
    """Run full diagnostic from in-memory tables (used for uploads, filters, and defaults)."""
    w_norm = normalization.normalize_wireless(w_raw)
    f_melt = normalization.normalize_fiber(f_raw)

    w_kpis = compute_wireless_kpis(w_norm)
    f_kpis = compute_fiber_kpis(f_raw, f_melt)
    baseline = combined_baseline(w_kpis, f_kpis)

    variance_df = variance_vs_benchmark(baseline["category_shares"], b_raw)
    idx_info = index_comparison(b_raw, w_kpis["cost_per_site"], w_kpis["cost_per_tb"])
    segments = segment_highlights(w_norm, b_raw)

    opps = build_opportunities(baseline, variance_df, idx_info)
    insight_text = generate_insights(baseline, variance_df, idx_info, opps)

    dyn = dynamic_peer_benchmark(
        b_raw,
        w_kpis["cost_per_site"],
        w_kpis["cost_per_tb"],
        baseline,
    )
    idx_info["dynamic_peer_benchmark"] = dyn

    data_health = compute_data_health(w_raw, f_raw, w_norm)
    semantic_metrics = compute_all_metrics(baseline, idx_info)
    ranked_insights = build_ranked_insights(
        baseline, variance_df, idx_info, dyn, opps
    )

    out: dict[str, Any] = {
        "paths": {"wireless": source_label or "in-memory", "fiber": source_label or "in-memory", "benchmarks": source_label or "in-memory"},
        "wireless_normalized": w_norm,
        "fiber_melt": f_melt,
        "fiber_raw": f_raw,
        "benchmarks": b_raw,
        "baseline": baseline,
        "variance_vs_benchmark": variance_df,
        "index_comparison": idx_info,
        "segment_highlights": segments,
        "opportunities": opps,
        "insights": insight_text,
        "data_health": data_health,
        "semantic_metrics": semantic_metrics,
        "ranked_insights": ranked_insights,
        "dynamic_peer_benchmark": dyn,
    }
    return out


def run_analysis(
    wireless_path: Optional[str] = None,
    fiber_path: Optional[str] = None,
    benchmarks_path: Optional[str] = None,
) -> dict[str, Any]:
    w_path, f_path, b_path = ingestion.resolve_default_paths(wireless_path, fiber_path, benchmarks_path)

    w_raw = ingestion.load_workbook(w_path)
    f_raw = ingestion.load_workbook(f_path)
    b_raw = ingestion.load_benchmarks(b_path)

    result = analyze_dataframes(w_raw, f_raw, b_raw, source_label="file")
    result["paths"] = {"wireless": str(w_path), "fiber": str(f_path), "benchmarks": str(b_path)}
    return result
