"""Rule-based and optional LLM-assisted mapping to standard cost taxonomy."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

import pandas as pd

from taxonomy import CATEGORIES

# Order matters: first match wins (more specific rules first).
RULE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"workforce|labor|wage|staff|field\s*ops|install|dispatch|noc", re.I), "Labor / Workforce"),
    (re.compile(r"oem|vendor|third[\s-]?party|managed\s*service|contractor|msoc|supplier", re.I), "Vendor / Third-party"),
    (re.compile(r"backhaul|transport|microwave|mw\s|fiber\s*bh|circuit|haul", re.I), "Transport / Backhaul"),
    (re.compile(r"tower|collocation|collo|lease|small\s*cell|site\s*rent|fiber\s*asset|strand", re.I), "Infrastructure"),
    (re.compile(r"ops|o&m|maintenance|maint|fuel|power|gen|spares|logistics", re.I), "Operations & Maintenance"),
]


def rule_based_category(text: str) -> Optional[str]:
    if not isinstance(text, str) or not text.strip():
        return None
    for pat, cat in RULE_PATTERNS:
        if pat.search(text):
            return cat
    return None


def _openai_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def llm_classify_descriptions(unmapped: list[str], model: Optional[str] = None) -> dict[str, str]:
    """Map free-text line descriptions to taxonomy categories using an LLM."""
    if not unmapped:
        return {}
    if not _openai_available():
        return {u: "Operations & Maintenance" for u in unmapped}

    from openai import OpenAI

    client = OpenAI()
    m = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    prompt = (
        "You classify telecom network cost line items into exactly one category per line.\n"
        f"Categories: {CATEGORIES}\n"
        "Respond with JSON only: {\"mappings\": [{\"line\": \"...\", \"category\": \"...\"}, ...]}\n"
        "Lines:\n"
        + "\n".join(f"- {u}" for u in unmapped)
    )
    resp = client.chat.completions.create(
        model=m,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
        out: dict[str, str] = {}
        for item in data.get("mappings", []):
            line = item.get("line")
            cat = item.get("category")
            if line in unmapped and cat in CATEGORIES:
                out[line] = cat
        for u in unmapped:
            if u not in out:
                out[u] = "Operations & Maintenance"
        return out
    except (json.JSONDecodeError, TypeError):
        return {u: "Operations & Maintenance" for u in unmapped}


def normalize_wireless(df: pd.DataFrame, desc_col: str = "Cost_Line_Description") -> pd.DataFrame:
    out = df.copy()
    if desc_col not in out.columns:
        # fuzzy pick
        for c in out.columns:
            if "cost" in c.lower() and "line" in c.lower():
                desc_col = c
                break
        else:
            desc_col = out.columns[0]

    cats: list[Optional[str]] = []
    for v in out[desc_col].astype(str):
        cats.append(rule_based_category(v))

    unmapped_idx = [i for i, c in enumerate(cats) if c is None]
    if unmapped_idx:
        unique_unmapped = list(dict.fromkeys(str(out.iloc[i][desc_col]) for i in unmapped_idx))
        llm_map = llm_classify_descriptions(unique_unmapped)
        for i in unmapped_idx:
            key = str(out.iloc[i][desc_col])
            cats[i] = llm_map.get(key, "Operations & Maintenance")

    out["standard_category"] = cats
    out["network"] = "Wireless"
    return out


def _find_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        if cand.lower() in lower:
            return lower[cand.lower()]
    for c in df.columns:
        cl = c.lower()
        for cand in candidates:
            if cand.lower() in cl:
                return c
    return None


def normalize_fiber(df: pd.DataFrame) -> pd.DataFrame:
    """Melt wide fiber cost columns into long form with standard categories."""
    col_map = [
        (["Labor_install_support_USD", "labor", "Labor"], "Labor / Workforce"),
        (["Third_party_construction_MSOC", "third_party", "vendor"], "Vendor / Third-party"),
        (["Transport_agg_USD", "transport"], "Transport / Backhaul"),
        (["Fiber_asset_OPEX_USD", "fiber_asset", "infrastructure"], "Infrastructure"),
        (["Ops_and_field_USD", "ops", "Opex"], "Operations & Maintenance"),
        (["Build_Capex_Alloc_USD", "build", "capex"], "Infrastructure"),
    ]
    resolved = [(cat, _find_col(df, cands)) for cands, cat in col_map]
    rows = []
    for _, r in df.iterrows():
        market = r.get("Market_Segment") or r.get("market") or "Fiber"
        hp = float(r.get("Homes_Passed") or r.get("homes_passed") or 0)
        hc = float(r.get("Homes_Connected") or r.get("homes_connected") or 0)
        for cat, col in resolved:
            if col is None:
                continue
            val = r.get(col)
            if pd.isna(val):
                continue
            rows.append(
                {
                    "Market_Segment": market,
                    "Homes_Passed": hp,
                    "Homes_Connected": hc,
                    "standard_category": cat,
                    "Amount_USD": float(val),
                    "network": "Fiber",
                    "row_tag": "fiber_melt",
                }
            )

    if not rows:
        return pd.DataFrame(columns=["standard_category", "Amount_USD", "network"])

    return pd.DataFrame(rows)
