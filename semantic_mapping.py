"""Semantic-style column → canonical field ranking (embedding-like without heavy deps).

Uses token overlap + character n-gram similarity against canonical field descriptions.
Optional: set USE_SKLEARN_EMBEDDINGS and install scikit-learn for TF–IDF cosine.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Callable, Iterable, Optional

# Rich text anchors per canonical role (wireless / fiber / benchmark use subsets)
CANON_FIELD_DOCS: dict[str, str] = {
    "Site_ID": "unique site identifier tower cell bts enodeb node location code",
    "Cost_Line_Description": "gl account description line item cost category ledger narrative",
    "Amount_USD": "amount spend dollars usd cost value currency payment total",
    "Density": "urban suburban rural market density geography population",
    "Traffic_TB_annual": "traffic terabyte tb annual data volume throughput gb",
    "Market": "market region state area territory dma footprint",
    "Market_Segment": "fiber market segment region territory broadband",
    "Homes_Passed": "homes passed passings hp premises available",
    "Homes_Connected": "homes connected subscribers customers take rate hc",
    "Labor_install_support_USD": "labor workforce install field support wages",
    "Third_party_construction_MSOC": "vendor third party contractor msoc construction oem",
    "Third_party_construction_MSOC_USD": "vendor third party contractor msoc construction oem",
    "Transport_agg_USD": "transport backhaul microwave circuit haul connectivity",
    "Fiber_asset_OPEX_USD": "fiber strand asset opex lease colocation infrastructure",
    "Ops_and_field_USD": "operations maintenance o&m field ops noc dispatch",
    "Build_Capex_Alloc_USD": "build capital capex construction allocation",
    "Peer_Operator": "peer operator company name competitor benchmark",
    "Operator_Type": "operator tier national regional type classification",
    "Density_Segment": "density segment urban rural suburban peer mix",
    "Category": "cost category taxonomy bucket classification",
    "Share_of_Network_Cost": "share percent percentage weight of network cost",
    "Cost_per_site_index": "index cost per site relative benchmark",
    "Cost_per_TB_index": "index cost per terabyte traffic normalized",
    "Cost_per_site_USD": "dollars per site annual cost per site usd",
    "Cost_per_TB_USD": "dollars per tb traffic unit cost",
}


def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def _bow(text: str) -> Counter[str]:
    return Counter(_tokens(text))


def _cosine_bow(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b.get(t, 0) for t in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return dot / (na * nb)


def _char_ngrams(s: str, n: int = 3) -> Counter[str]:
    s = re.sub(r"\s+", " ", s.lower().strip())
    if len(s) < n:
        return Counter([s] if s else [])
    return Counter(s[i : i + n] for i in range(len(s) - n + 1))


def _similarity_column_to_doc(column_name: str, doc: str) -> float:
    col = str(column_name)
    c_bow = _bow(col)
    d_bow = _bow(doc)
    lex = 0.62 * _cosine_bow(c_bow, d_bow) + 0.38 * _cosine_bow(_char_ngrams(col), _char_ngrams(doc))
    return float(min(1.0, lex))


def rank_canonical_matches(
    column_name: str,
    candidate_canon_fields: Iterable[str],
    sample_values: Optional[list[str]] = None,
    top_k: int = 3,
) -> list[tuple[str, float]]:
    """Return (canonical_field, score 0–1) sorted descending."""
    extra = ""
    if sample_values:
        joined = " ".join(str(v)[:80] for v in sample_values[:25] if _is_present(v))
        extra = " " + joined
    col_blob = str(column_name) + extra
    scores: list[tuple[str, float]] = []
    for field in candidate_canon_fields:
        doc = CANON_FIELD_DOCS.get(field, field.replace("_", " "))
        s = _similarity_column_to_doc(col_blob, doc)
        scores.append((field, s))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]


def _is_present(v: object) -> bool:
    try:
        import pandas as pd

        return not pd.isna(v)
    except Exception:
        return v is not None and str(v).strip() != ""


def suggest_semantic_column_mapping(
    columns: list[str],
    canon_fields: list[str],
    df_sample_fn: Optional[Callable[[str], list[str]]] = None,
) -> dict[str, list[tuple[str, float]]]:
    """For each source column, top semantic matches to canon fields."""
    out: dict[str, list[tuple[str, float]]] = {}
    for col in columns:
        samples: list[str] = []
        if df_sample_fn is not None:
            try:
                samples = df_sample_fn(col)
            except Exception:
                samples = []
        out[col] = rank_canonical_matches(col, canon_fields, samples)
    return out
