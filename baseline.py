"""Unified cost model: wireless and fiber KPIs and category breakdown."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from taxonomy import CATEGORIES


def compute_wireless_kpis(wireless_normalized: pd.DataFrame) -> dict[str, Any]:
    df = wireless_normalized.copy()
    if df.empty:
        return {
            "total_cost": 0.0,
            "n_sites": 0,
            "traffic_tb": 0.0,
            "cost_per_site": 0.0,
            "cost_per_tb": 0.0,
            "by_category": {c: 0.0 for c in CATEGORIES},
        }

    total = float(df["Amount_USD"].sum())
    n_sites = int(df["Site_ID"].nunique()) if "Site_ID" in df.columns else int(len(df))

    tb_col = "Traffic_TB_annual" if "Traffic_TB_annual" in df.columns else None
    if tb_col:
        tb = float(df.groupby("Site_ID", dropna=False)[tb_col].first().sum())
    else:
        tb = 0.0

    by_cat = df.groupby("standard_category")["Amount_USD"].sum().reindex(CATEGORIES, fill_value=0.0)
    by_category = {k: float(v) for k, v in by_cat.items()}

    return {
        "total_cost": total,
        "n_sites": max(n_sites, 1),
        "traffic_tb": float(tb) if tb else 1.0,
        "cost_per_site": total / max(n_sites, 1),
        "cost_per_tb": total / max(float(tb), 1e-6),
        "by_category": by_category,
    }


def compute_fiber_kpis(fiber_wide: pd.DataFrame, fiber_melt: pd.DataFrame) -> dict[str, Any]:
    """Build vs operating split using wide table columns when present."""
    if fiber_wide is None or fiber_wide.empty:
        return {
            "total_cost": 0.0,
            "homes_passed": 0,
            "homes_connected": 0,
            "cost_per_home_passed": 0.0,
            "cost_per_home_connected": 0.0,
            "build_cost": 0.0,
            "operating_cost": 0.0,
            "build_share": 0.0,
            "by_category": {c: 0.0 for c in CATEGORIES},
        }

    fw = fiber_wide.copy()
    hp = float(fw.get("Homes_Passed", fw.get("homes_passed", pd.Series([0]))).sum())
    hc = float(fw.get("Homes_Connected", fw.get("homes_connected", pd.Series([0]))).sum())

    build_col = None
    for name in ["Build_Capex_Alloc_USD", "build_capex", "Build"]:
        if name in fw.columns:
            build_col = name
            break
    build_cost = float(fw[build_col].sum()) if build_col else 0.0

    if not fiber_melt.empty and "Amount_USD" in fiber_melt.columns:
        total = float(fiber_melt["Amount_USD"].sum())
        by_cat = fiber_melt.groupby("standard_category")["Amount_USD"].sum().reindex(CATEGORIES, fill_value=0.0)
    else:
        # Sum known numeric columns
        num_cols = [c for c in fw.select_dtypes(include=[np.number]).columns if c not in ("Homes_Passed", "homes_passed", "Homes_Connected", "homes_connected")]
        total = float(fw[num_cols].sum().sum()) if num_cols else 0.0
        by_cat = pd.Series(0.0, index=CATEGORIES)

    by_category = {k: float(v) for k, v in by_cat.items()}
    operating_cost = max(total - build_cost, 0.0)

    return {
        "total_cost": total,
        "homes_passed": int(hp),
        "homes_connected": int(hc),
        "cost_per_home_passed": total / max(hp, 1.0),
        "cost_per_home_connected": total / max(hc, 1.0),
        "build_cost": build_cost,
        "operating_cost": operating_cost,
        "build_share": build_cost / total if total else 0.0,
        "by_category": by_category,
    }


def combined_baseline(w_kpis: dict[str, Any], f_kpis: dict[str, Any]) -> dict[str, Any]:
    total = w_kpis["total_cost"] + f_kpis["total_cost"]
    combined_cat = {c: w_kpis["by_category"].get(c, 0) + f_kpis["by_category"].get(c, 0) for c in CATEGORIES}
    shares = {c: (combined_cat[c] / total) if total else 0.0 for c in CATEGORIES}
    return {
        "total_network_cost": total,
        "wireless_share": w_kpis["total_cost"] / total if total else 0.0,
        "fiber_share": f_kpis["total_cost"] / total if total else 0.0,
        "wireless": w_kpis,
        "fiber": f_kpis,
        "combined_by_category": combined_cat,
        "category_shares": shares,
    }
