"""Auto-detect spreadsheet columns and apply user-confirmed mappings."""
from __future__ import annotations

import re
from typing import Optional

import pandas as pd

# Canonical internal names -> regex patterns (first match wins per role)
WIRELESS_ROLES: list[tuple[str, re.Pattern]] = [
    ("Site_ID", re.compile(r"site[_\s-]?id|site\s*code|bts|enodeb", re.I)),
    ("Cost_Line_Description", re.compile(r"cost.*line|description|line\s*item|category|gl|account", re.I)),
    ("Amount_USD", re.compile(r"amount|usd|cost\s*\(|spend|value", re.I)),
    ("Density", re.compile(r"density|urban|rural|geo|market\s*type", re.I)),
    ("Traffic_TB_annual", re.compile(r"traffic|tb|volume|data", re.I)),
    ("Market", re.compile(r"market|region|area|state", re.I)),
]

FIBER_ROLES: list[tuple[str, re.Pattern]] = [
    ("Market_Segment", re.compile(r"market|segment|region", re.I)),
    ("Homes_Passed", re.compile(r"homes?\s*passed|passings|hp\b", re.I)),
    ("Homes_Connected", re.compile(r"homes?\s*connected|subs|customers|hc\b", re.I)),
    ("Labor_install_support_USD", re.compile(r"labor|install|support|workforce", re.I)),
    ("Third_party_construction_MSOC", re.compile(r"third|vendor|construction|msoc|contractor", re.I)),
    ("Transport_agg_USD", re.compile(r"transport|backhaul|haul", re.I)),
    ("Fiber_asset_OPEX_USD", re.compile(r"fiber.*asset|asset.*opex|strand|network\s*asset", re.I)),
    ("Ops_and_field_USD", re.compile(r"ops|field|o&m|maintenance|operations", re.I)),
    ("Build_Capex_Alloc_USD", re.compile(r"build|capex|capital|construction\s*alloc", re.I)),
]

BENCHMARK_ROLES: list[tuple[str, re.Pattern]] = [
    ("Peer_Operator", re.compile(r"peer|operator|company|name", re.I)),
    ("Operator_Type", re.compile(r"operator\s*type|tier|national|regional", re.I)),
    ("Density_Segment", re.compile(r"density|urban|rural|segment", re.I)),
    ("Category", re.compile(r"category|taxonomy|bucket", re.I)),
    ("Share_of_Network_Cost", re.compile(r"share|percent|pct|weight", re.I)),
    ("Cost_per_site_index", re.compile(r"site.*index|cpi\s*site", re.I)),
    ("Cost_per_TB_index", re.compile(r"tb.*index|traffic.*index", re.I)),
    ("Cost_per_site_USD", re.compile(r"site.*usd|\$.*site|cost.*per\s*site", re.I)),
    ("Cost_per_TB_USD", re.compile(r"tb.*usd|per\s*tb", re.I)),
]


def _first_match(columns: list[str], roles: list[tuple[str, re.Pattern]]) -> dict[str, str]:
    used: set[str] = set()
    out: dict[str, str] = {}
    for canon, pat in roles:
        for c in columns:
            if c in used:
                continue
            if pat.search(c):
                out[canon] = c
                used.add(c)
                break
    return out


def suggest_wireless_mapping(columns: list[str]) -> dict[str, str]:
    return _first_match(list(columns), WIRELESS_ROLES)


def suggest_fiber_mapping(columns: list[str]) -> dict[str, str]:
    return _first_match(list(columns), FIBER_ROLES)


def suggest_benchmark_mapping(columns: list[str]) -> dict[str, str]:
    return _first_match(list(columns), BENCHMARK_ROLES)


def apply_mapping(df: pd.DataFrame, mapping: dict[str, Optional[str]]) -> pd.DataFrame:
    """Rename user column names to canonical internal names. Skips empty selections."""
    rev = {}
    for k, v in mapping.items():
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        rev[s] = k
    return df.rename(columns=rev)
