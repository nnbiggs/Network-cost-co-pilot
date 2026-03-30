"""Compare normalized costs to peer benchmarks: variance, percentiles, outliers."""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from taxonomy import CATEGORIES


def _peer_frame(benchmarks: pd.DataFrame) -> pd.DataFrame:
    b = benchmarks.copy()
    if "Peer_Operator" in b.columns:
        b = b[b["Peer_Operator"].astype(str).str.contains("Your Network", case=False) == False]
    return b


def category_benchmark_table(benchmarks: pd.DataFrame) -> pd.DataFrame:
    """Median share by category across peers (excludes 'Your Network' row if present)."""
    b = _peer_frame(benchmarks)
    if b.empty or "Category" not in b.columns:
        return pd.DataFrame()
    col = "Share_of_Network_Cost" if "Share_of_Network_Cost" in b.columns else b.select_dtypes(include=[np.number]).columns[0]
    g = b.groupby("Category")[col].agg(["median", "mean", "std", "min", "max"]).reset_index()
    return g


def variance_vs_benchmark(
    observed_shares: dict[str, float],
    benchmarks: pd.DataFrame,
) -> pd.DataFrame:
    """Percent variance of observed category share vs peer median."""
    medians = category_benchmark_table(benchmarks).set_index("Category")["median"].reindex(CATEGORIES)
    rows = []
    for c in CATEGORIES:
        obs = float(observed_shares.get(c, 0.0))
        bench = float(medians.get(c, np.nan))
        if bench and not np.isnan(bench):
            var_pct = (obs - bench) / bench * 100.0
        else:
            var_pct = 0.0
        rows.append(
            {
                "Category": c,
                "Observed_share": obs,
                "Benchmark_median_share": float(bench) if not np.isnan(bench) else None,
                "Variance_pct": var_pct,
            }
        )
    return pd.DataFrame(rows)


def percentile_and_zscore(
    value: float,
    peer_values: np.ndarray,
) -> tuple[Optional[float], Optional[float]]:
    if peer_values.size == 0:
        return None, None
    peer_values = np.sort(peer_values.astype(float))
    rank = np.searchsorted(peer_values, value, side="right")
    pct = 100.0 * rank / len(peer_values)
    mu = float(np.mean(peer_values))
    sigma = float(np.std(peer_values))
    z = (value - mu) / sigma if sigma > 1e-9 else 0.0
    return pct, z


def index_comparison(
    benchmarks: pd.DataFrame,
    observed_cost_per_site: float,
    observed_cost_per_tb: float,
) -> dict[str, Any]:
    """Compare site and TB costs to peer benchmarks (dollars and indices when present)."""
    b = _peer_frame(benchmarks)
    out: dict[str, Any] = {"peers": []}
    if b.empty:
        return out

    cps_idx = "Cost_per_site_index" if "Cost_per_site_index" in b.columns else None
    cpt_idx = "Cost_per_TB_index" if "Cost_per_TB_index" in b.columns else None
    cps_usd = "Cost_per_site_USD" if "Cost_per_site_USD" in b.columns else None
    cpt_usd = "Cost_per_TB_USD" if "Cost_per_TB_USD" in b.columns else None

    peer_site_idx = b[cps_idx].dropna().values if cps_idx else np.array([])
    peer_tb_idx = b[cpt_idx].dropna().values if cpt_idx else np.array([])

    if cps_usd and "Peer_Operator" in b.columns:
        peer_site_usd = b.drop_duplicates("Peer_Operator")[cps_usd].astype(float).values
    elif cps_usd:
        peer_site_usd = b[cps_usd].dropna().astype(float).values
    else:
        peer_site_usd = np.array([])

    if cpt_usd and "Peer_Operator" in b.columns:
        peer_tb_usd = b.drop_duplicates("Peer_Operator")[cpt_usd].astype(float).values
    elif cpt_usd:
        peer_tb_usd = b[cpt_usd].dropna().astype(float).values
    else:
        peer_tb_usd = np.array([])

    med_site_usd = float(np.median(peer_site_usd)) if peer_site_usd.size else None
    med_tb_usd = float(np.median(peer_tb_usd)) if peer_tb_usd.size else None

    site_idx = 100.0 * (observed_cost_per_site / med_site_usd) if med_site_usd else 100.0
    tb_idx = 100.0 * (observed_cost_per_tb / med_tb_usd) if med_tb_usd else 100.0

    ps, zs = percentile_and_zscore(site_idx, peer_site_idx) if peer_site_idx.size else (None, None)
    pt, zt = percentile_and_zscore(tb_idx, peer_tb_idx) if peer_tb_idx.size else (None, None)

    ps_usd, zs_usd = (
        percentile_and_zscore(observed_cost_per_site, peer_site_usd) if peer_site_usd.size else (None, None)
    )
    pt_usd, zt_usd = (
        percentile_and_zscore(observed_cost_per_tb, peer_tb_usd) if peer_tb_usd.size else (None, None)
    )

    peer_rows = b.drop_duplicates(subset=["Peer_Operator"]) if "Peer_Operator" in b.columns else b.head(5)
    for _, row in peer_rows.iterrows():
        out["peers"].append(
            {
                "name": row.get("Peer_Operator", ""),
                "operator_type": row.get("Operator_Type", ""),
                "density": row.get("Density_Segment", ""),
                "cost_per_site_index": row.get(cps_idx) if cps_idx else None,
                "cost_per_tb_index": row.get(cpt_idx) if cpt_idx else None,
                "cost_per_site_usd": row.get(cps_usd) if cps_usd else None,
                "cost_per_tb_usd": row.get(cpt_usd) if cpt_usd else None,
            }
        )

    site_var_pct = (
        (observed_cost_per_site - med_site_usd) / med_site_usd * 100.0 if med_site_usd else None
    )
    tb_var_pct = (observed_cost_per_tb - med_tb_usd) / med_tb_usd * 100.0 if med_tb_usd else None

    out.update(
        {
            "benchmark_median_cost_per_site_usd": med_site_usd,
            "benchmark_median_cost_per_tb_usd": med_tb_usd,
            "observed_cost_per_site_index": site_idx,
            "observed_cost_per_tb_index": tb_idx,
            "variance_pct_cost_per_site_vs_peer_median": site_var_pct,
            "variance_pct_cost_per_tb_vs_peer_median": tb_var_pct,
            "percentile_site_index": ps,
            "z_site_index": zs,
            "percentile_tb_index": pt,
            "z_tb_index": zt,
            "percentile_cost_per_site_usd": ps_usd,
            "percentile_cost_per_tb_usd": pt_usd,
        }
    )
    return out


def segment_highlights(
    wireless_normalized: pd.DataFrame,
    benchmarks: pd.DataFrame,
) -> dict[str, Any]:
    """Urban vs rural cost intensity (proxy) and regional vs national benchmark split."""
    w = wireless_normalized
    rural_premium = None
    if w.empty or "Density" not in w.columns:
        rural_premium = {}
    else:
        rural = w[w["Density"].astype(str).str.contains("Rural", case=False)]
        urban = w[w["Density"].astype(str).str.contains("Urban|Suburban", case=False, regex=True)]
        r_cost = float(rural["Amount_USD"].sum()) / max(len(rural["Site_ID"].unique()) if "Site_ID" in rural.columns else 1, 1)
        u_cost = float(urban["Amount_USD"].sum()) / max(len(urban["Site_ID"].unique()) if "Site_ID" in urban.columns else 1, 1)
        rural_premium = {"rural_cost_per_site_proxy": r_cost, "urban_suburban_cost_per_site_proxy": u_cost}

    b = benchmarks.copy()
    seg = {}
    if "Operator_Type" in b.columns and "Share_of_Network_Cost" in b.columns:
        for seg_name in ["Regional", "National"]:
            sub = b[b["Operator_Type"] == seg_name]
            if not sub.empty:
                seg[seg_name] = sub.groupby("Category")["Share_of_Network_Cost"].median().to_dict()

    return {"rural_urban": rural_premium, "benchmark_by_operator_type": seg}


def build_benchmark_heatmap_df(
    variance_df: pd.DataFrame,
) -> pd.DataFrame:
    """Single-row heatmap: variance % per category."""
    return variance_df.set_index("Category")[["Variance_pct"]].T


def _peer_operator_table(benchmarks: pd.DataFrame) -> pd.DataFrame:
    """One row per peer operator with cost and segmentation features."""
    b = _peer_frame(benchmarks)
    if b.empty or "Peer_Operator" not in b.columns:
        return pd.DataFrame()
    cps = "Cost_per_site_USD" if "Cost_per_site_USD" in b.columns else None
    cpt = "Cost_per_TB_USD" if "Cost_per_TB_USD" in b.columns else None
    if not cps:
        return pd.DataFrame()
    rows = []
    for name, sub in b.groupby("Peer_Operator", dropna=False):
        site_series = pd.to_numeric(sub[cps], errors="coerce").dropna()
        if site_series.empty:
            continue
        row: dict[str, Any] = {
            "Peer_Operator": name,
            "cost_per_site_usd": float(site_series.iloc[0]),
            "operator_type": "",
            "density": "",
        }
        if "Operator_Type" in sub.columns and sub["Operator_Type"].notna().any():
            row["operator_type"] = str(sub["Operator_Type"].dropna().iloc[0])
        if "Density_Segment" in sub.columns and sub["Density_Segment"].notna().any():
            row["density"] = str(sub["Density_Segment"].dropna().iloc[0])
        if cpt:
            tb_series = pd.to_numeric(sub[cpt], errors="coerce").dropna()
            row["cost_per_tb_usd"] = float(tb_series.iloc[0]) if not tb_series.empty else float("nan")
        rows.append(row)
    g = pd.DataFrame(rows)
    if g.empty:
        return g
    return g.dropna(subset=["cost_per_site_usd"])


def dynamic_peer_benchmark(
    benchmarks: pd.DataFrame,
    observed_cost_per_site: float,
    observed_cost_per_tb: float,
    baseline: dict[str, Any],
    k_peers: int = 5,
) -> dict[str, Any]:
    """
    Cluster-like peer set: similarity by cost scale, operator type, and density segment.
    Compares you to median of nearest peers in normalized feature space.
    """
    out: dict[str, Any] = {
        "similar_peer_names": [],
        "peer_group_label": "all peers",
        "median_cost_per_site_similar": None,
        "median_cost_per_tb_similar": None,
        "variance_pct_site_vs_similar": None,
        "variance_pct_tb_vs_similar": None,
        "n_similar": 0,
        "narrative": "",
    }
    pt = _peer_operator_table(benchmarks)
    if pt.empty or len(pt) < 2:
        return out
    if observed_cost_per_site <= 0:
        out["narrative"] = "Wireless cost-per-site is not in scope for this view — similar-peer site comparison skipped."
        return out

    # Observed profile
    w_share = float(baseline.get("wireless_share") or 0.0)
    f_share = float(baseline.get("fiber_share") or 0.0)
    network_mix = "fiber_heavy" if f_share > w_share + 0.15 else ("wireless_heavy" if w_share > f_share + 0.15 else "balanced")

    def _type_code(t: str) -> float:
        s = str(t).lower()
        if "national" in s or "tier" in s:
            return 1.0
        if "regional" in s:
            return 0.0
        return 0.5

    def _density_code(d: str) -> float:
        s = str(d).lower()
        if "rural" in s:
            return 1.0
        if "urban" in s or "metro" in s:
            return 0.0
        return 0.5

    peers = pt.copy()
    peers["f1"] = np.log1p(peers["cost_per_site_usd"].clip(lower=1.0))
    peers["f2"] = peers["operator_type"].map(_type_code)
    peers["f3"] = peers["density"].map(_density_code)

    mu1, sig1 = peers["f1"].mean(), peers["f1"].std() or 1.0
    peers["z1"] = (peers["f1"] - mu1) / sig1
    peers["z2"] = peers["f2"]
    peers["z3"] = peers["f3"]

    obs_f1 = np.log1p(max(observed_cost_per_site, 1.0))
    z_obs1 = (obs_f1 - mu1) / sig1
    # Assume regional, blended density from network mix proxy
    z_obs2 = 0.0 if network_mix != "fiber_heavy" else 0.2
    z_obs3 = 0.7 if network_mix == "wireless_heavy" else 0.4

    mat = peers[["z1", "z2", "z3"]].values.astype(float)
    obs = np.array([z_obs1, z_obs2, z_obs3], dtype=float)
    dist = np.sqrt(((mat - obs) ** 2).sum(axis=1))
    peers["_dist"] = dist
    k = min(k_peers, len(peers))
    nearest = peers.nsmallest(k, "_dist")

    med_site = float(nearest["cost_per_site_usd"].median())
    med_tb = None
    if "cost_per_tb_usd" in nearest.columns and nearest["cost_per_tb_usd"].notna().any():
        med_tb = float(nearest["cost_per_tb_usd"].median())

    out["similar_peer_names"] = nearest["Peer_Operator"].astype(str).tolist()
    out["n_similar"] = len(nearest)
    out["median_cost_per_site_similar"] = med_site
    out["median_cost_per_tb_similar"] = med_tb
    out["peer_group_label"] = f"{k} most similar peers (scale, type, density)"

    if med_site:
        out["variance_pct_site_vs_similar"] = (observed_cost_per_site - med_site) / med_site * 100.0
    if med_tb and observed_cost_per_tb:
        out["variance_pct_tb_vs_similar"] = (observed_cost_per_tb - med_tb) / med_tb * 100.0

    # Narrative
    vs = out["variance_pct_site_vs_similar"]
    if vs is not None:
        direction = "above" if vs > 0 else "below"
        tier = "similar regional-style operators" if z_obs2 < 0.6 else "peers with comparable scale profiles"
        out["narrative"] = (
            f"You are **{abs(vs):.0f}% {direction}** vs **{tier}** on cost per site "
            f"(not a single static average — based on **{out['n_similar']}** closest peer matches)."
        )
    else:
        out["narrative"] = "Not enough peer segmentation to form a similar-peer cohort."

    out["network_mix_tag"] = network_mix
    return out
