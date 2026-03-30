"""
PwC One — Network Cost Intelligence: Streamlit client experience for telecom cost diagnostics.

Live demo talk track: see README.md section "Live demo talk track".
"""
from __future__ import annotations

import io
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from column_mapping import (
    apply_mapping,
    suggest_benchmark_mapping,
    suggest_fiber_mapping,
    suggest_wireless_mapping,
)
from executive_narrative import (
    benchmark_plain_insight,
    executive_story_mode,
    executive_summary_lines,
)
from explainability import explain_index_comparison, explain_opportunity, explain_variance_row
from insight_engine import answer_question
from semantic_mapping import suggest_semantic_column_mapping
from simulation import run_scenario
from filters import (
    NETWORK_COMBINED,
    NETWORK_FIBER,
    NETWORK_WIRELESS,
    REGION_ALL,
    REGION_METRO,
    REGION_RURAL,
    filter_network,
    filter_wireless_region,
)
import ingestion
from pipeline import analyze_dataframes
from taxonomy import CATEGORIES
from ui_copy import METRIC_HELP, business_category_name, top_concentration_phrase
from pwc_experience import (
    DEMO_PHASES,
    PRODUCT_SUBTITLE,
    PRODUCT_TITLE,
    SECURE_WORKSPACE_NOTE,
    STORYLINE_COMPRESSION,
    TRUST_STRIP,
    VALUE_PROPOSITION,
    build_executive_panel,
    phase_headline,
)
from user_help import render_sidebar_help_teaser, render_user_guide

_ASSETS = Path(__file__).resolve().parent / "assets"
PWC_LOGO_PATH = _ASSETS / "pwc_logo.svg"

st.set_page_config(
    page_title="PwC One — Network Cost Intelligence",
    page_icon=str(PWC_LOGO_PATH) if PWC_LOGO_PATH.exists() else "◆",
    layout="wide",
    initial_sidebar_state="auto",
)

RISK_COLOR = "#c0392b"
OPP_COLOR = "#1e8449"
NEUTRAL = "#64748b"

PHASE_OVERVIEW = "Overview"
PHASE_INGEST = "1 · Ingest & standardize"
PHASE_BASELINE = "2 · Integrated cost baseline"
PHASE_BENCHMARK = "3 · Peer benchmark comparison"
PHASE_INSIGHTS = "4 · AI-assisted gap insights"
PHASE_ROADMAP = "5 · Prioritized action roadmap"
PHASE_LABELS = [
    PHASE_OVERVIEW,
    PHASE_INGEST,
    PHASE_BASELINE,
    PHASE_BENCHMARK,
    PHASE_INSIGHTS,
    PHASE_ROADMAP,
]

CANON_W = [
    "Site_ID",
    "Cost_Line_Description",
    "Amount_USD",
    "Density",
    "Traffic_TB_annual",
    "Market",
]
CANON_F = [
    "Market_Segment",
    "Homes_Passed",
    "Homes_Connected",
    "Labor_install_support_USD",
    "Third_party_construction_MSOC",
    "Transport_agg_USD",
    "Fiber_asset_OPEX_USD",
    "Ops_and_field_USD",
    "Build_Capex_Alloc_USD",
]
CANON_B = [
    "Peer_Operator",
    "Operator_Type",
    "Density_Segment",
    "Category",
    "Share_of_Network_Cost",
    "Cost_per_site_index",
    "Cost_per_TB_index",
    "Cost_per_site_USD",
    "Cost_per_TB_USD",
]


def _usd(n: float | None) -> str:
    if n is None:
        return "—"
    if abs(n) >= 1_000_000:
        return f"${n/1_000_000:.2f}M"
    if abs(n) >= 1_000:
        return f"${n/1_000:.0f}K"
    return f"${n:,.0f}"


def _init_state() -> None:
    if "w_raw" not in st.session_state:
        try:
            w, f, b = ingestion.load_default_dataframes()
            st.session_state.w_raw = w
            st.session_state.f_raw = f
            st.session_state.b_raw = b
            st.session_state.using_example = True
        except FileNotFoundError:
            st.session_state.w_raw = pd.DataFrame()
            st.session_state.f_raw = pd.DataFrame()
            st.session_state.b_raw = pd.DataFrame()
            st.session_state.using_example = False
    if "workflow" not in st.session_state:
        st.session_state.workflow = {}
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


@st.cache_data(show_spinner=False)
def _cached_analyze(w_json: str, f_json: str, b_json: str) -> dict[str, Any]:
    w = pd.read_json(io.StringIO(w_json), orient="split")
    f = pd.read_json(io.StringIO(f_json), orient="split")
    b = pd.read_json(io.StringIO(b_json), orient="split")
    return analyze_dataframes(w, f, b, source_label="cached")


def run_filtered_analysis(
    w_raw: pd.DataFrame,
    f_raw: pd.DataFrame,
    b_raw: pd.DataFrame,
    region: str,
    network: str,
) -> dict[str, Any]:
    w1 = filter_wireless_region(w_raw, region)
    w2, f2 = filter_network(w1, f_raw, network)
    wj = w2.to_json(orient="split", date_format="iso")
    fj = f2.to_json(orient="split", date_format="iso")
    bj = b_raw.to_json(orient="split", date_format="iso")
    return _cached_analyze(wj, fj, bj)


def _mapping_select(
    label: str,
    columns: list[str],
    canon: str,
    suggested: Optional[str],
    key_suffix: str,
) -> str:
    opts = [""] + list(columns)
    default = suggested if suggested in columns else (columns[0] if columns else "")
    idx = opts.index(default) if default in opts else 0
    return st.selectbox(
        f"{label} → **{canon}**",
        options=opts,
        index=idx,
        format_func=lambda x: "(skip)" if x == "" else x,
        key=f"map_{key_suffix}_{label}_{canon}",
    )


def render_executive_summary(result: dict[str, Any]) -> None:
    base = result["baseline"]
    idx = result["index_comparison"]
    var = result["variance_vs_benchmark"]
    opps = result["opportunities"]
    lines = executive_summary_lines(base, idx, opps)
    insight_b = benchmark_plain_insight(var, idx)

    st.markdown("### Executive snapshot")
    st.markdown(lines["peer"])
    st.markdown(lines["top"])
    st.markdown(lines["savings"])
    st.markdown(insight_b)


def _phase_number(phase: str) -> int:
    try:
        return PHASE_LABELS.index(phase) + 1
    except ValueError:
        return 1


def render_pwc_brand_marks(*, sidebar: bool = False) -> None:
    """PwC logo — trademark; see assets/README.md."""
    if not PWC_LOGO_PATH.exists():
        return
    if sidebar:
        st.image(str(PWC_LOGO_PATH), width=168)
    else:
        st.image(str(PWC_LOGO_PATH), width=88)


def render_phase_progress(phase: str) -> None:
    n = _phase_number(phase)
    label = phase if phase == PHASE_OVERVIEW else phase.split("·")[-1].strip()
    st.progress(min(n / float(len(PHASE_LABELS)), 1.0))
    st.caption(f"**Phase {n} of {len(PHASE_LABELS)}:** {label}")


def _phase_key(phase: str) -> str:
    return {
        PHASE_OVERVIEW: "overview",
        PHASE_INGEST: "ingest",
        PHASE_BASELINE: "baseline",
        PHASE_BENCHMARK: "benchmark",
        PHASE_INSIGHTS: "insights",
        PHASE_ROADMAP: "roadmap",
    }.get(phase, "overview")


def render_summary_cards(result: dict[str, Any], network: str) -> None:
    dh = result.get("data_health") or {}
    score = dh.get("data_health_score", "—")
    mc = dh.get("mapping_confidence_0_100", "—")
    idx = result["index_comparison"]
    opps = result["opportunities"]
    lo, hi = opps.get("total_savings_range", (0, 0))
    site_v = idx.get("variance_pct_cost_per_site_vs_peer_median")
    dyn = result.get("dynamic_peer_benchmark") or {}
    vsim = dyn.get("variance_pct_site_vs_similar")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "Data quality & coverage",
            f"{score}/100" if score != "—" else "—",
            help=f"Completeness, outliers, taxonomy signals. **Mapping confidence:** {mc}/100 — {dh.get('mapping_confidence_note', '')}"
            if mc != "—"
            else "Data health across ingested files.",
        )
    with c2:
        if network != NETWORK_FIBER and site_v is not None:
            st.metric(
                "Cost gap vs peers (wireless site)",
                f"{site_v:+.1f}%",
                delta=f"{site_v:+.1f}%",
                delta_color="inverse" if site_v > 3 else "normal",
                help="Peer benchmark comparison — cost per site vs median of benchmark file.",
            )
        else:
            st.metric("Cost gap vs peers (wireless site)", "—", help="Visible when wireless is in scope.")
    with c3:
        if vsim is not None and network != NETWORK_FIBER:
            st.metric(
                "Similar-peer position",
                f"{vsim:+.1f}%",
                help=dyn.get("peer_group_label", "Clustered peer benchmark — not a single industry average."),
            )
        else:
            st.metric("Similar-peer position", "—")
    with c4:
        st.metric(
            "Quantified opportunity range",
            f"{_usd(lo)} – {_usd(hi)}",
            help="Modeled quantified savings opportunities across levers — for steering discussion, not a guarantee.",
        )


def main() -> None:
    _init_state()

    with st.sidebar:
        render_pwc_brand_marks(sidebar=True)
        st.markdown(f"### {PRODUCT_TITLE}")
        app_view = st.radio(
            "View",
            ["Analysis", "Help & instructions"],
            horizontal=False,
            key="app_view_mode",
            help="Switch to the full user guide without leaving the app.",
        )
        if app_view == "Analysis":
            render_sidebar_help_teaser()
        st.divider()
        st.caption("Created by **Nigel Biggs**")

    if app_view == "Help & instructions":
        render_user_guide()
        return

    h1, h2 = st.columns([1, 10], gap="small")
    with h1:
        render_pwc_brand_marks(sidebar=False)
    with h2:
        st.markdown(f"### {PRODUCT_TITLE}")
        st.caption(PRODUCT_SUBTITLE)
        st.caption(SECURE_WORKSPACE_NOTE)
    st.markdown(f"<div style='background:linear-gradient(135deg,#1e293b 0%,#334155 100%);color:#f8fafc;padding:1.5rem 1.75rem;border-radius:12px;margin:0.5rem 0 1.25rem 0;line-height:1.55;'>{VALUE_PROPOSITION}</div>", unsafe_allow_html=True)
    st.info(f"{STORYLINE_COMPRESSION}\n\n{TRUST_STRIP}")
    st.caption("📖 **User guide:** Sidebar → **Help & instructions**.")

    phase = st.radio(
        "Guided experience — PwC One Network Cost Intelligence",
        PHASE_LABELS,
        horizontal=True,
        label_visibility="collapsed",
    )
    render_phase_progress(phase)

    region = REGION_ALL
    network = NETWORK_COMBINED
    if phase != PHASE_INGEST:
        fx1, fx2, _ = st.columns([1, 1, 2])
        with fx1:
            region = st.selectbox(
                "Geography scope",
                [REGION_ALL, REGION_METRO, REGION_RURAL],
                index=0,
                help="Focus on metro & suburban sites, rural sites, or the full footprint (where density data exists).",
            )
        with fx2:
            network = st.selectbox(
                "Network scope",
                [NETWORK_COMBINED, NETWORK_WIRELESS, NETWORK_FIBER],
                index=0,
                help="Integrated baseline, wireless-only, or fiber-only view.",
            )

    w_raw = st.session_state.w_raw
    f_raw = st.session_state.f_raw
    b_raw = st.session_state.b_raw

    if phase == PHASE_INGEST:
        st.markdown(f"#### {PHASE_INGEST}")
        st.caption(
            "AI-assisted alignment of fragmented extracts into a **common PwC network cost taxonomy** — low friction, high traceability."
        )

        a, b = st.columns([1, 1])
        with a:
            st.markdown("**Drag and drop** or browse — CSV or Excel for each stream.")
            u_w = st.file_uploader("Wireless / mobile network costs", type=["csv", "xlsx", "xls"])
            u_f = st.file_uploader("Fiber / broadband costs", type=["csv", "xlsx", "xls"])
            u_b = st.file_uploader("Peer benchmark comparison file", type=["csv", "xlsx", "xls"])
        with b:
            if st.button("Use example telecom dataset", use_container_width=True, type="primary"):
                try:
                    w, f, b = ingestion.load_default_dataframes()
                    st.session_state.w_raw = w
                    st.session_state.f_raw = f
                    st.session_state.b_raw = b
                    st.session_state.using_example = True
                    st.rerun()
                except FileNotFoundError as e:
                    st.error(str(e))
            st.info(
                "Representative telecom data loads on first visit so you can experience the full **PwC One** storyline end-to-end. "
                "Upload all three files when you are ready to substitute client-style extracts."
            )

        if u_w and u_f and u_b:
            w_df = ingestion.load_uploaded_file(u_w, u_w.name)
            f_df = ingestion.load_uploaded_file(u_f, u_f.name)
            b_df = ingestion.load_uploaded_file(u_b, u_b.name)

            sw = suggest_wireless_mapping(list(w_df.columns))
            sf = suggest_fiber_mapping(list(f_df.columns))
            sb = suggest_benchmark_mapping(list(b_df.columns))

            with st.expander("Preview uploaded data (first rows)", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.caption("Wireless")
                    st.dataframe(w_df.head(5), use_container_width=True, height=180)
                with c2:
                    st.caption("Fiber")
                    st.dataframe(f_df.head(5), use_container_width=True, height=180)
                with c3:
                    st.caption("Benchmarks")
                    st.dataframe(b_df.head(5), use_container_width=True, height=180)

            with st.expander("AI-assisted field mapping (semantic similarity)", expanded=False):
                st.caption(
                    "**PwC One-style intelligent assistance:** each source column is ranked against the **standard network cost model** "
                    "using semantic similarity (token + character n-grams). Use with **professional judgment** to confirm mappings."
                )
                sw2 = suggest_semantic_column_mapping(
                    list(w_df.columns),
                    CANON_W,
                    lambda col: w_df[col].dropna().astype(str).head(25).tolist(),
                )
                sf2 = suggest_semantic_column_mapping(
                    list(f_df.columns),
                    CANON_F,
                    lambda col: f_df[col].dropna().astype(str).head(25).tolist(),
                )
                sb2 = suggest_semantic_column_mapping(
                    list(b_df.columns),
                    CANON_B,
                    lambda col: b_df[col].dropna().astype(str).head(25).tolist(),
                )
                t1, t2, t3 = st.tabs(["Wireless hints", "Fiber hints", "Benchmark hints"])
                with t1:
                    for col, ranks in list(sw2.items())[:20]:
                        top = ranks[0] if ranks else ("", 0)
                        st.write(f"**{col}** → best: `{top[0]}` ({top[1]:.0%})")
                with t2:
                    for col, ranks in list(sf2.items())[:20]:
                        top = ranks[0] if ranks else ("", 0)
                        st.write(f"**{col}** → best: `{top[0]}` ({top[1]:.0%})")
                with t3:
                    for col, ranks in list(sb2.items())[:20]:
                        top = ranks[0] if ranks else ("", 0)
                        st.write(f"**{col}** → best: `{top[0]}` ({top[1]:.0%})")

            with st.expander("Confirm column mapping to PwC network cost taxonomy", expanded=False):
                st.caption(
                    "Maps your fields to the **integrated taxonomy** (labor, vendor, backhaul, infrastructure, operations). "
                    "Leave a field blank if not present. **PwC teams** validate mappings in live engagements."
                )
                map_uid = f"{u_w.name}|{u_f.name}|{u_b.name}"
                st.markdown("**Wireless**")
                mw = {c: _mapping_select("Wireless", list(w_df.columns), c, sw.get(c), map_uid) for c in CANON_W}
                st.markdown("**Fiber**")
                mf = {c: _mapping_select("Fiber", list(f_df.columns), c, sf.get(c), map_uid) for c in CANON_F}
                st.markdown("**Benchmarks**")
                mb = {c: _mapping_select("Benchmark", list(b_df.columns), c, sb.get(c), map_uid) for c in CANON_B}

                if st.button("Use these files & mappings", type="primary", use_container_width=True):
                    try:
                        w_m = apply_mapping(w_df, mw)
                        f_m = apply_mapping(f_df, mf)
                        b_m = apply_mapping(b_df, mb)
                        if "Amount_USD" not in w_m.columns:
                            st.error("Wireless file needs an amount column mapped to **Amount_USD**.")
                        else:
                            st.session_state.w_raw = w_m
                            st.session_state.f_raw = f_m
                            st.session_state.b_raw = b_m
                            st.session_state.using_example = False
                            st.success("Data ingested and standardized. Continue to **Integrated cost baseline** or **Overview**.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Could not apply mapping: {e}")

        if st.session_state.get("using_example"):
            st.warning(
                "Session is using the **example telecom dataset** — suitable for executive demos. "
                "Upload client extracts in **Ingest & standardize** when demonstrating with client-like data."
            )

        st.stop()

    if getattr(b_raw, "empty", True) or (w_raw.empty and f_raw.empty):
        if phase == PHASE_OVERVIEW:
            st.markdown("#### Executive overview")
            st.caption(phase_headline("overview"))
            st.warning(
                "Connect **wireless**, **fiber**, and **peer benchmark** data under **Ingest & standardize** to populate this view."
            )
            st.markdown("**Demo storyline (live narrative):**")
            for i, line in enumerate(DEMO_PHASES, 1):
                st.markdown(f"{i}. {line}")
            st.stop()
        st.error("Benchmark and cost files are required. Complete **Ingest & standardize**.")
        st.stop()

    result = run_filtered_analysis(w_raw, f_raw, b_raw, region, network)

    if phase == PHASE_OVERVIEW:
        st.markdown("#### Executive overview")
        st.caption(phase_headline("overview"))
        panel = build_executive_panel(result, network)
        e1, e2, e3, e4 = st.columns(4)
        lo, hi = panel["estimated_savings_range"]
        idx_o = result["index_comparison"]
        site_gap = idx_o.get("variance_pct_cost_per_site_vs_peer_median")
        with e1:
            if network != NETWORK_FIBER and site_gap is not None:
                st.metric(
                    "Total cost gap vs peers (wireless site)",
                    f"{site_gap:+.1f}%",
                    delta=f"{site_gap:+.1f}%",
                    delta_color="inverse" if site_gap > 3 else "normal",
                    help="Peer benchmark comparison — cost per site vs benchmark median.",
                )
            else:
                st.metric("Total cost gap vs peers (wireless site)", "—", help="Add wireless to scope to view.")
        top_lev = str(panel["top_optimization_lever"])
        with e2:
            st.metric(
                "Top optimization lever",
                (top_lev[:32] + "…") if len(top_lev) > 34 else top_lev,
                help=top_lev,
            )
        with e3:
            st.metric("Estimated savings range", f"{_usd(lo)} – {_usd(hi)}", help="Modeled quantified savings opportunities.")
        with e4:
            mc = panel.get("mapping_confidence")
            dq = panel.get("data_health_score", "—")
            st.metric(
                "Data quality & mapping confidence",
                f"{dq}/100 · {mc}/100" if mc is not None else f"{dq}/100",
                help="Coverage, outliers, taxonomy; mapping confidence reflects canonical field strength.",
            )
        st.markdown(panel["cost_gap_summary"])
        st.markdown("##### Priority actions (steering-committee ready)")
        for pa in panel.get("priority_actions") or []:
            st.markdown(f"- **{pa['title']}** — {pa['savings']}")
        st.markdown("---")
        st.markdown("##### Snapshot — same KPIs as deeper phases")
        st.caption(
            f"<span style='color:{RISK_COLOR};font-weight:600;'>Above peer</span> = cost pressure · "
            f"<span style='color:{OPP_COLOR};font-weight:600;'>Below peer</span> = favorable position",
            unsafe_allow_html=True,
        )
        render_summary_cards(result, network)
        render_executive_summary(result)
        st.stop()

    st.markdown("##### Executive snapshot (this phase)")
    st.caption(phase_headline(_phase_key(phase)))
    st.caption(
        f"<span style='color:{RISK_COLOR};font-weight:600;'>Above peer</span> = cost pressure · "
        f"<span style='color:{OPP_COLOR};font-weight:600;'>Below peer</span> = favorable",
        unsafe_allow_html=True,
    )
    render_summary_cards(result, network)
    render_executive_summary(result)

    base = result["baseline"]
    var = result["variance_vs_benchmark"]
    idx = result["index_comparison"]
    opps = result["opportunities"]
    w = base["wireless"]
    f = base["fiber"]

    if phase == PHASE_BASELINE:
        st.markdown(f"#### {PHASE_BASELINE}")
        st.caption(
            "A single **integrated cost baseline** across wireless and fiber — business labels, AI-assisted intelligence, PwC judgment on interpretation."
        )

        dh = result.get("data_health") or {}
        st.markdown("##### Data quality, mapping confidence & health")
        col_h, col_h2, col_w = st.columns([1, 1, 2])
        with col_h:
            sc = dh.get("data_health_score", "—")
            band = dh.get("data_health_band", "")
            st.metric("Data quality score", f"{sc}/100", help="Completeness, outliers, taxonomy and transport signals.")
            st.caption(band or "")
        with col_h2:
            mc = dh.get("mapping_confidence_0_100", "—")
            st.metric("Mapping confidence", f"{mc}/100" if mc != "—" else "—", help=dh.get("mapping_confidence_note", ""))
        with col_w:
            for wmsg in dh.get("warnings", [])[:6]:
                st.warning(wmsg, icon="⚠️")

        with st.expander("Defined metrics (semantic layer — single source of truth)", expanded=False):
            st.caption("Consistent KPI definitions across the engagement; extend in `metrics_layer.py` for your operating model.")
            sm = result.get("semantic_metrics") or {}
            rows = []
            for mid, m in sm.items():
                v = m.get("value")
                u = m.get("unit")
                if v is None:
                    disp = "—"
                elif u == "ratio":
                    disp = f"{v*100:.1f}%"
                else:
                    disp = _usd(v)
                rows.append(
                    {
                        "Metric": m.get("title", mid),
                        "Value": disp,
                        "Formula": m.get("formula", ""),
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        total = base["total_network_cost"]
        st.metric(
            "Integrated network cost (annual, in scope)",
            _usd(total),
            help=METRIC_HELP["total_cost"],
        )

        conc = top_concentration_phrase(base["category_shares"], top_n=2)
        st.markdown("##### Narrative — integrated baseline")
        st.markdown(conc)

        c1, c2 = st.columns([1, 1])
        with c1:
            mix = pd.DataFrame(
                {
                    "Network": ["Wireless", "Fiber"],
                    "Spend": [w["total_cost"], f["total_cost"]],
                }
            )
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=mix["Network"],
                        values=mix["Spend"],
                        hole=0.52,
                        marker=dict(colors=["#3b82f6", "#10b981"]),
                        textinfo="label+percent",
                        hovertemplate="%{label}<br>%{percent}<br>%{value:$,.0f}<extra></extra>",
                    )
                ]
            )
            fig.update_layout(
                title="Wireless vs fiber — share of integrated spend",
                showlegend=False,
                height=380,
                margin=dict(t=50, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            cat_rows = []
            for c in CATEGORIES:
                cat_rows.append(
                    {
                        "Area": business_category_name(c),
                        "Share of spend": base["category_shares"].get(c, 0) * 100,
                    }
                )
            cdf = pd.DataFrame(cat_rows).sort_values("Share of spend", ascending=True)
            fig2 = go.Figure(
                go.Bar(
                    x=cdf["Share of spend"],
                    y=cdf["Area"],
                    orientation="h",
                    marker_color="#64748b",
                    hovertemplate="%{y}<br>%{x:.1f}% of spend<extra></extra>",
                )
            )
            fig2.update_layout(
                title="Cost stack — labor, vendor, backhaul, infrastructure, operations",
                height=380,
                xaxis_title="Percent of integrated total",
                margin=dict(t=50, b=20),
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.info(
            "**PwC perspective:** Most integrated networks concentrate spend in **people & field**, **vendors**, and **backhaul** — "
            "the **Peer benchmark comparison** phase quantifies how your profile compares."
        )

    elif phase == PHASE_BENCHMARK:
        st.markdown(f"#### {PHASE_BENCHMARK}")
        st.caption(
            "**Peer benchmark comparison** with **similar-peer clustering** — above peer = cost pressure vs benchmark; below = favorable. "
            "Charts use **red / green** to highlight position vs **peer median**."
        )

        dyn = result.get("dynamic_peer_benchmark") or {}
        if dyn.get("narrative") and network != NETWORK_FIBER:
            peers_named = ", ".join(dyn.get("similar_peer_names") or [])
            st.info(f"**Tailored peer benchmark (similar-peer clustering):** {dyn['narrative']}")
            if peers_named:
                st.caption(f"Similar peer cohort: {peers_named}")

        if network == NETWORK_FIBER:
            st.info(
                "You’re viewing **fiber only** — wireless site metrics are hidden because they’re out of scope for this filter."
            )

        metrics = st.columns(3)
        med_site = idx.get("benchmark_median_cost_per_site_usd")
        med_tb = idx.get("benchmark_median_cost_per_tb_usd")
        site_v = idx.get("variance_pct_cost_per_site_vs_peer_median")
        tb_v = idx.get("variance_pct_cost_per_tb_vs_peer_median")

        with metrics[0]:
            st.metric(
                "Wireless — cost per site",
                _usd(w["cost_per_site"]) if network != NETWORK_FIBER else "—",
                delta=f"{site_v:+.1f}% vs peer median" if network != NETWORK_FIBER and site_v is not None else None,
                help=METRIC_HELP["cost_per_site"],
            )
        with metrics[1]:
            st.metric(
                "Wireless — cost per TB (traffic-normalized)",
                _usd(w["cost_per_tb"]) if network != NETWORK_FIBER else "—",
                delta=f"{tb_v:+.1f}% vs peer median" if network != NETWORK_FIBER and tb_v is not None else None,
                help=METRIC_HELP["cost_per_tb"],
            )
        with metrics[2]:
            st.metric(
                "Fiber — cost per home passed",
                _usd(f["cost_per_home_passed"]) if network != NETWORK_WIRELESS else "—",
                help="Annual fiber-attributed spend divided by homes passed.",
            )

        st.markdown("##### Interpretation — peer benchmark comparison")
        st.markdown(benchmark_plain_insight(var, idx))

        if network != NETWORK_FIBER and med_site and med_tb:
            obs_site = w["cost_per_site"]
            obs_tb = w["cost_per_tb"]
            colors_site = ["#c0392b" if obs_site > med_site else "#1e8449", "#7f8c8d"]
            colors_tb = ["#c0392b" if obs_tb > med_tb else "#1e8449", "#7f8c8d"]

            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    name="You",
                    x=["Cost per site", "Cost per unit of traffic"],
                    y=[obs_site, obs_tb],
                    marker_color=[colors_site[0], colors_tb[0]],
                    hovertemplate="You: %{y:$,.0f}<extra></extra>",
                )
            )
            fig.add_trace(
                go.Bar(
                    name="Peer median",
                    x=["Cost per site", "Cost per unit of traffic"],
                    y=[med_site, med_tb],
                    marker_color="#95a5a6",
                    hovertemplate="Peer median: %{y:$,.0f}<extra></extra>",
                )
            )
            fig.update_layout(
                barmode="group",
                title="Your network vs peer median — wireless intensity",
                height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.05),
                margin=dict(t=60, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "**Above peer median** (red) = higher unit cost vs benchmark file; **green** = lower. "
                "Use **AI-assisted gap insights** for root-cause narrative and suggested actions."
            )

    elif phase == PHASE_INSIGHTS:
        st.markdown(f"#### {PHASE_INSIGHTS}")
        st.caption(
            "AI-assisted cost intelligence surfaces **structural drivers** of gaps; **PwC judgment** validates and frames implications for leadership."
        )
        ranked = result.get("ranked_insights") or []
        for card in ranked[:8]:
            sev = card.get("severity") or "watch"
            border = RISK_COLOR if sev == "risk" else (OPP_COLOR if sev == "opportunity" else NEUTRAL)
            st.markdown(
                f"<div style='border-left:4px solid {border};padding:1rem 1rem 1rem 1.1rem;margin:12px 0;background:#fafafa;border-radius:0 8px 8px 0;'>"
                f"<div style='font-size:0.75rem;text-transform:uppercase;letter-spacing:0.04em;color:#64748b;'>Insight</div>"
                f"<strong style='font-size:1.05rem;color:#0f172a;'>{card.get('title','')}</strong><br/>"
                f"<span style='color:#334155;line-height:1.5;'>{card.get('narrative') or card.get('body','')}</span><br/><br/>"
                f"<span style='color:#0f172a;'><b>Why this matters</b></span><br/><span style='color:#475569;'>{card.get('why_matters','')}</span><br/><br/>"
                f"<span style='color:#0f172a;'><b>What the data supports</b></span><br/><span style='color:#475569;'>{card.get('data_supports','')}</span><br/><br/>"
                f"<span style='color:#0f172a;'><b>Suggested action</b></span><br/><span style='color:#475569;'>{card.get('suggested_action','')}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            with st.expander(f"Why this insight? — traceability & benchmark logic — {card.get('title', '')[:36]}"):
                st.caption(
                    "**AI accelerates pattern detection; PwC teams validate** mappings, benchmarks, and business context before client decisions."
                )
                st.write("**Drivers considered:** " + "; ".join(card.get("drivers") or []))
                st.write("**Data references:** " + ", ".join(card.get("data_refs") or []))
                if card["id"].startswith("var_"):
                    cat = card["id"].replace("var_", "", 1)
                    ex = explain_variance_row(var, cat)
                    st.write(ex.get("summary", ""))
                    for s in ex.get("steps", []):
                        st.caption(s)
                elif card["id"] == "idx_site":
                    ex = explain_index_comparison(idx, "site")
                    for s in ex.get("steps", []):
                        st.caption(s)
                elif card["id"] == "idx_tb":
                    ex = explain_index_comparison(idx, "tb")
                    for s in ex.get("steps", []):
                        st.caption(s)
                elif card["id"] == "similar_peers":
                    st.caption(
                        "Similar peers = nearest neighbors in **z-scored log(cost/site)**, **operator type**, and **density segment** "
                        "vs a profile inferred from your wireless/fiber mix."
                    )

    elif phase == PHASE_ROADMAP:
        st.markdown(f"#### {PHASE_ROADMAP}")
        st.caption(
            "**Quantified savings opportunities**, sequencing, scenarios, and **prioritized action roadmap** — structured for steering committees. "
            "**PwC judgment** applied to AI-generated findings."
        )

        lo, hi = opps["total_savings_range"]
        st.success(
            f"**Quantified savings opportunities (modeled range):** {_usd(lo)} – {_usd(hi)} annualized — "
            f"{METRIC_HELP['savings_range']}"
        )

        st.markdown("##### Prioritized roadmap — sequencing & impact")
        st.caption("**Quick wins** = higher feasibility / shorter time-to-value; **medium-term** and **longer-cycle** for steering discussion.")
        qw = opps.get("quick_wins") or []
        lt = opps.get("longer_term") or []
        ids_q = {x.get("lever_id") for x in qw}
        ids_l = {x.get("lever_id") for x in lt}
        medium = [
            i
            for i in (opps.get("initiatives") or [])
            if i.get("lever_id") not in ids_q and i.get("lever_id") not in ids_l
        ]

        def _roadmap_rows(items: list) -> None:
            for it in items:
                st.markdown(
                    f"- **{it.get('business_title') or it.get('title')}** — {_usd(it.get('savings_low_usd'))}–{_usd(it.get('savings_high_usd'))} · "
                    f"feasibility **{it.get('effort')}** · time to value **{it.get('time_to_value', it.get('time_to_implement', '—'))}**"
                )

        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown("**Phase A — Quick wins**")
            _roadmap_rows(qw)
        with r2:
            st.markdown("**Phase B — Medium-term**")
            _roadmap_rows(medium)
        with r3:
            st.markdown("**Phase C — Longer-cycle**")
            _roadmap_rows(lt)

        with st.expander("Executive summary — export layout (steering committee)", expanded=False):
            story = executive_story_mode(
                base,
                idx,
                opps,
                result.get("ranked_insights") or [],
                result.get("dynamic_peer_benchmark") or {},
                result.get("data_health") or {},
            )
            st.markdown(f"### {story['title']}")
            st.markdown("**Key findings**")
            for fl in story.get("findings", []):
                st.markdown(f"- {fl}")
            st.markdown("**Top opportunities**")
            for o in story.get("opportunities", []):
                st.markdown(f"- {o}")
            st.markdown(f"**Estimated savings:** {story.get('estimated_savings', '')}")
            st.markdown(story.get("data_health", ""))
            st.caption(story.get("footer", ""))

        st.markdown("##### Scenario modeling — savings assumptions")
        st.caption(
            "Stress-test **quantified savings opportunities** under explicit assumptions; **PwC teams** calibrate scenarios with client finance."
        )
        s1, s2, s3 = st.columns(3)
        with s1:
            v_cut = st.slider("Vendor optimization — cost reduction %", 0, 25, 0, help="Applied to vendor & supplier taxonomy bucket.")
            l_prod = st.slider("Workforce efficiency — productivity gain %", 0, 25, 0, help="Modeled as effective labor cost reduction.")
        with s2:
            t_cut = st.slider("Backhaul optimization — reduction %", 0, 25, 0)
            i_cut = st.slider("Infrastructure rationalization — reduction %", 0, 20, 0)
        with s3:
            n_cut = st.slider("Network operations improvement — efficiency %", 0, 20, 0)
        scen = run_scenario(
            base,
            vendor_cost_reduction_pct=v_cut / 100.0,
            labor_productivity_pct=l_prod / 100.0,
            transport_reduction_pct=t_cut / 100.0,
            infrastructure_reduction_pct=i_cut / 100.0,
            netops_efficiency_pct=n_cut / 100.0,
        )
        st.metric(
            "Modeled scenario impact (annual)",
            _usd(scen["total_savings_usd"]),
            help="Directional; PwC validates assumptions with client finance and network engineering.",
        )
        ex = scen["kpi_deltas"]["cost_per_site"]
        if ex["before"] > 0:
            st.caption(
                f"Wireless cost/site: {_usd(ex['before'])} → {_usd(ex['after'])} · "
                f"Cost/TB: {_usd(scen['kpi_deltas']['cost_per_tb']['before'])} → {_usd(scen['kpi_deltas']['cost_per_tb']['after'])}"
            )
        st.caption(scen.get("assumptions", ""))

        st.markdown("##### Quantified opportunities — by category")
        st.caption(
            "Initiatives grouped for **vendor**, **workforce**, **backhaul**, **infrastructure**, and **network operations** — "
            "each with **feasibility**, **time to value**, and **confidence**."
        )
        by_cat: dict[str, list] = defaultdict(list)
        for ini in sorted(opps.get("initiatives") or [], key=lambda x: -x.get("priority_score", 0)):
            by_cat[ini.get("pwc_category") or "Cost optimization"].append(ini)

        top = opps.get("top_5", [])[:5]
        top_ids = {x.get("lever_id") for x in top[:2]}
        shown = 0
        for cat_name in sorted(by_cat.keys()):
            st.markdown(f"###### {cat_name}")
            for i, item in enumerate(by_cat[cat_name]):
                shown += 1
                title = item.get("business_title") or item.get("title")
                effort = item.get("effort", "Medium")
                lid = item.get("lever_id") or str(shown)
                tag = ""
                if item.get("lever_id") in top_ids:
                    tag = '<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:6px;font-size:0.8rem;font-weight:600;">Prioritize</span>'
                savings_txt = f"{_usd(item['savings_low_usd'])} – {_usd(item['savings_high_usd'])}"
                conf = item.get("confidence_0_100", "—")
                cx = item.get("complexity_tier", "Medium")
                ttv = item.get("time_to_value") or item.get("time_to_implement", "—")
                desc = item.get("initiative_description") or ""
                action = item.get("recommended_action", "")
                body = (
                    f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:1rem 1.1rem;margin-bottom:0.75rem;background:#fff;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">'
                    f'<div style="font-size:1.05rem;font-weight:600;color:#111827;">{title}</div>{tag}</div>'
                    f'<div style="color:#64748b;margin-top:0.25rem;font-size:0.92rem;">{desc}</div>'
                    f'<div style="color:#475569;margin-top:0.35rem;">Savings range: <strong>{savings_txt}</strong> · '
                    f'Feasibility: <strong>{effort}</strong> · Complexity: <strong>{cx}</strong> · '
                    f'Time to value: <strong>{ttv}</strong> · Confidence: <strong>{conf}/100</strong></div>'
                    f'<div style="color:#334155;margin-top:0.5rem;font-size:0.95rem;"><b>Recommended move:</b> {action}</div></div>'
                )
                st.markdown(body, unsafe_allow_html=True)
                with st.expander(f"Traceability · {title[:40]}"):
                    st.caption("**PwC judgment** validates initiative sizing, feasibility, and client readiness.")
                    exo = explain_opportunity(item, base)
                    st.write(exo.get("summary", ""))
                    for s in exo.get("steps", []):
                        st.caption(s)

        st.markdown("##### Client workspace — owners & status")
        st.caption("Session workspace to **tag**, **assign**, and **track** initiatives (full PwC One deployments persist to secure collaboration).")
        wf = st.session_state.workflow
        for i, item in enumerate(top):
            lid = item.get("lever_id") or str(i)
            row = wf.get(lid, {"tags": "", "owner": "", "status": "Not started"})
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            with c1:
                st.text(item.get("business_title") or item.get("title") or lid)
            with c2:
                tags = st.text_input("Tags", value=row["tags"], key=f"wf_tags_{lid}", placeholder="e.g. Q3, backhaul")
            with c3:
                owner = st.text_input("Owner", value=row["owner"], key=f"wf_owner_{lid}")
            with c4:
                status = st.selectbox(
                    "Status",
                    ["Not started", "In progress", "Done"],
                    index=["Not started", "In progress", "Done"].index(row["status"])
                    if row["status"] in ("Not started", "In progress", "Done")
                    else 0,
                    key=f"wf_status_{lid}",
                )
            wf[lid] = {"tags": tags, "owner": owner, "status": status}
        st.session_state.workflow = wf

        st.markdown("##### Natural language — ask the intelligence layer")
        st.caption(
            'Examples: **"Why are my costs higher?"** · **"Where is the biggest savings opportunity?"** · **"What should we do first?"**'
        )
        for msg in st.session_state.chat_messages[-12:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        q = st.chat_input("Ask a question about your integrated baseline and peer benchmarks…")
        if q:
            st.session_state.chat_messages.append({"role": "user", "content": q})
            ans = answer_question(
                q,
                base,
                var,
                idx,
                opps,
                result.get("ranked_insights") or [],
            )
            st.session_state.chat_messages.append({"role": "assistant", "content": ans})
            st.rerun()

        st.markdown("---")
        st.caption(
            "Optional **OpenAI** integration (`OPENAI_API_KEY`) can extend narrative depth; **this experience is fully usable** with rule-based, traceable intelligence."
        )


if __name__ == "__main__":
    main()
