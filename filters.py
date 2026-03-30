"""Filter raw cost tables for region and network-type views."""
from __future__ import annotations

import pandas as pd

REGION_ALL = "All areas"
REGION_METRO = "Metro & suburban"
REGION_RURAL = "Rural"

NETWORK_COMBINED = "Wireless + fiber (combined)"
NETWORK_WIRELESS = "Wireless only"
NETWORK_FIBER = "Fiber only"


def filter_wireless_region(w_raw: pd.DataFrame, region: str) -> pd.DataFrame:
    if w_raw.empty or region == REGION_ALL:
        return w_raw.copy()
    col = None
    for c in w_raw.columns:
        if str(c).lower() == "density" or "density" in str(c).lower():
            col = c
            break
    if col is None:
        return w_raw.copy()
    s = w_raw[col].astype(str)
    if region == REGION_METRO:
        mask = s.str.contains(r"Urban|Suburban", case=False, regex=True, na=False)
        return w_raw.loc[mask].copy()
    if region == REGION_RURAL:
        mask = s.str.contains("Rural", case=False, na=False)
        return w_raw.loc[mask].copy()
    return w_raw.copy()


def filter_network(
    w_raw: pd.DataFrame,
    f_raw: pd.DataFrame,
    network: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if network == NETWORK_COMBINED:
        return w_raw.copy(), f_raw.copy()
    if network == NETWORK_WIRELESS:
        cols = list(f_raw.columns) if f_raw is not None and len(f_raw.columns) else []
        return w_raw.copy(), pd.DataFrame(columns=cols)
    if network == NETWORK_FIBER:
        cols = list(w_raw.columns) if w_raw is not None and len(w_raw.columns) else []
        return pd.DataFrame(columns=cols), f_raw.copy()
    return w_raw.copy(), f_raw.copy()
