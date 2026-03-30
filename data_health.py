"""Data quality, schema inference, and Data Health Score (0–100)."""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd


def infer_schema(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Per-column inferred dtype category and null rate."""
    rows = []
    for c in df.columns:
        s = df[c]
        null_pct = float(s.isna().mean()) if len(s) else 0.0
        kind = str(s.dtype)
        if pd.api.types.is_numeric_dtype(s):
            role = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(s):
            role = "datetime"
        else:
            role = "text"
        rows.append({"column": str(c), "pandas_dtype": kind, "role": role, "null_pct": round(null_pct * 100, 2)})
    return rows


def _iqr_outlier_rate(series: pd.Series) -> float:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 10:
        return 0.0
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = float(q3 - q1)
    if iqr < 1e-9:
        return 0.0
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    out = ((s < low) | (s > high)).mean()
    return float(out)


def _transport_missing_by_site(w_norm: pd.DataFrame) -> Optional[float]:
    """Share of sites with no transport-tagged spend (proxy for backhaul gap)."""
    if w_norm.empty or "Site_ID" not in w_norm.columns or "standard_category" not in w_norm.columns:
        return None
    t = w_norm[w_norm["standard_category"] == "Transport / Backhaul"]
    sites_with = set(t["Site_ID"].astype(str).unique())
    all_sites = w_norm["Site_ID"].astype(str).unique()
    if len(all_sites) == 0:
        return None
    missing_share = 1.0 - (len(sites_with) / len(all_sites))
    return float(max(0.0, min(1.0, missing_share)))


def compute_data_health(
    w_raw: pd.DataFrame,
    f_raw: pd.DataFrame,
    w_normalized: pd.DataFrame,
) -> dict[str, Any]:
    """
    Produce score, warnings, and checks for wireless + fiber inputs.
    w_normalized: after taxonomy mapping (for category/site checks).
    """
    score = 100.0
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []

    # Wireless
    if not w_raw.empty:
        schema_w = infer_schema(w_raw)
        checks.append({"dataset": "wireless", "schema": schema_w})
        if "Amount_USD" in w_raw.columns:
            miss = float(w_raw["Amount_USD"].isna().mean())
            if miss > 0:
                deduct = min(25.0, miss * 80)
                score -= deduct
                warnings.append(f"Wireless **Amount_USD** missing on **{miss*100:.0f}%** of rows.")
            out_rate = _iqr_outlier_rate(w_raw["Amount_USD"])
            if out_rate > 0.08:
                score -= min(15.0, out_rate * 40)
                warnings.append(
                    f"Wireless spend shows **{out_rate*100:.0f}%** potential outliers (IQR rule) — validate units and capex vs opex."
                )
        else:
            score -= 12
            warnings.append("Wireless file has no **Amount_USD** column after mapping — cannot score spend quality.")

        if "Site_ID" in w_raw.columns:
            site_miss = float(w_raw["Site_ID"].isna().mean())
            if site_miss > 0.05:
                score -= min(10.0, site_miss * 50)
                warnings.append(f"**Site_ID** missing on **{site_miss*100:.0f}%** of wireless rows.")

        if "Traffic_TB_annual" in w_raw.columns:
            tmiss = float(w_raw["Traffic_TB_annual"].isna().mean())
            if tmiss > 0.15:
                score -= 8
                warnings.append(f"Traffic (**Traffic_TB_annual**) missing on **{tmiss*100:.0f}%** of rows — cost-per-TB less reliable.")
    else:
        warnings.append("Wireless dataset is **empty** for this view.")

    # Fiber
    if not f_raw.empty:
        schema_f = infer_schema(f_raw)
        checks.append({"dataset": "fiber", "schema": schema_f})
        num_cols = [c for c in f_raw.select_dtypes(include=[np.number]).columns]
        if num_cols:
            for c in num_cols[:6]:
                miss = float(f_raw[c].isna().mean())
                if miss > 0.2:
                    warnings.append(f"Fiber column **{c}** missing **{miss*100:.0f}%** — check extracts.")
                    score -= 4
    else:
        warnings.append("Fiber dataset is **empty** for this view.")

    # Normalized: backhaul coverage
    if w_normalized is not None and not w_normalized.empty:
        trans_gap = _transport_missing_by_site(w_normalized)
        if trans_gap is not None and trans_gap >= 0.12:
            score -= min(12.0, trans_gap * 30)
            warnings.append(
                f"**Backhaul / transport** costs appear missing for **{trans_gap*100:.0f}%** of sites (no transport-tagged lines) — confirm mapping."
            )
        if "standard_category" in w_normalized.columns:
            unk = w_normalized["standard_category"].isna().mean()
            if unk > 0.05:
                score -= min(8.0, unk * 40)
                warnings.append(f"**{unk*100:.0f}%** of wireless lines lack a confident taxonomy category.")

    score = float(max(0.0, min(100.0, round(score, 1))))
    band = "Strong" if score >= 80 else ("Fair" if score >= 60 else "Needs attention")

    return {
        "data_health_score": score,
        "data_health_band": band,
        "warnings": warnings,
        "checks": checks,
    }
