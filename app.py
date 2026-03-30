"""AI-powered network cost optimization co-pilot — guided analytics, benchmarks, simulation."""
from __future__ import annotations

import io
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
from user_help import render_sidebar_help_teaser, render_user_guide

st.set_page_config(
    page_title="Network cost co-pilot",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="auto",
)

RISK_COLOR = "#c0392b"
OPP_COLOR = "#1e8449"
NEUTRAL = "#64748b"

STEP_LABELS = [
    "1 · Data",
    "2 · Spending",
    "3 · Comparison",
    "4 · Actions",
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

    st.markdown("### At-a-glance")
    st.markdown(lines["peer"])
    st.markdown(lines["top"])
    st.markdown(lines["savings"])
    st.markdown(insight_b)


def _step_number(step: str) -> int:
    try:
        return STEP_LABELS.index(step) + 1
    except ValueError:
        return 1


def render_step_progress(step: str) -> None:
    n = _step_number(step)
    label = step.split("·")[-1].strip()
    st.progress(min(n / 4.0, 1.0))
    st.caption(f"**Step {n} of 4:** {label}")


def render_summary_cards(result: dict[str, Any], network: str) -> None:
    dh = result.get("data_health") or {}
    score = dh.get("data_health_score", "—")
    idx = result["index_comparison"]
    opps = result["opportunities"]
    lo, hi = opps.get("total_savings_range", (0, 0))
    site_v = idx.get("variance_pct_cost_per_site_vs_peer_median")
    dyn = result.get("dynamic_peer_benchmark") or {}
    vsim = dyn.get("variance_pct_site_vs_similar")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Data health", f"{score}/100" if score != "—" else "—", help="Quality, completeness, taxonomy coverage.")
    with c2:
        if network != NETWORK_FIBER and site_v is not None:
            st.metric(
                "vs peer median (site)",
                f"{site_v:+.1f}%",
                delta=f"{site_v:+.1f}%",
                delta_color="inverse" if site_v > 3 else "normal",
            )
        else:
            st.metric("vs peer median (site)", "—")
    with c3:
        if vsim is not None and network != NETWORK_FIBER:
            st.metric("vs similar peers", f"{vsim:+.1f}%", help=dyn.get("peer_group_label", ""))
        else:
            st.metric("vs similar peers", "—")
    with c4:
        st.metric("Modeled savings range", f"{_usd(lo)} – {_usd(hi)}", help="Illustrative, from initiative levers.")


def main() -> None:
    _init_state()

    with st.sidebar:
        st.markdown("### Network cost co-pilot")
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

    st.markdown("### Network cost co-pilot")
    st.caption(
        "Scalable decision platform: smart ingestion, semantic metrics, dynamic benchmarks, explainable insights, "
        "scenarios, and workflow — evolve from dashboard to optimization partner."
    )
    st.caption("📖 **Help:** Open the sidebar → **Help & instructions** for step-by-step user guide and tips.")

    step = st.radio(
        "Guided steps",
        STEP_LABELS,
        horizontal=True,
        label_visibility="collapsed",
    )
    render_step_progress(step)

    region = REGION_ALL
    network = NETWORK_COMBINED
    if step != STEP_LABELS[0]:
        fx1, fx2, _ = st.columns([1, 1, 2])
        with fx1:
            region = st.selectbox(
                "Area focus",
                [REGION_ALL, REGION_METRO, REGION_RURAL],
                index=0,
                help="Focus the view on metro/suburban sites, rural sites, or the full footprint.",
            )
        with fx2:
            network = st.selectbox(
                "Network focus",
                [NETWORK_COMBINED, NETWORK_WIRELESS, NETWORK_FIBER],
                index=0,
                help="Look at wireless only, fiber only, or the combined picture.",
            )

    w_raw = st.session_state.w_raw
    f_raw = st.session_state.f_raw
    b_raw = st.session_state.b_raw

    if step == STEP_LABELS[0]:
        st.markdown("#### Step 1 · Bring your data")
        st.caption("Upload spreadsheets or use the example dataset — no training required.")

        a, b = st.columns([1, 1])
        with a:
            u_w = st.file_uploader("Wireless / mobile network costs (CSV or Excel)", type=["csv", "xlsx", "xls"])
            u_f = st.file_uploader("Fiber / broadband costs (CSV or Excel)", type=["csv", "xlsx", "xls"])
            u_b = st.file_uploader("Peer benchmark file (CSV or Excel)", type=["csv", "xlsx", "xls"])
        with b:
            if st.button("Try with example data", use_container_width=True):
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
                "Example data loads automatically on first visit. Upload all three files to replace it."
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

            with st.expander("Auto-mapping (semantic similarity to standard fields)", expanded=False):
                st.caption(
                    "Like a metrics layer in modern data platforms: we rank each source column against canonical roles "
                    "using token + n-gram similarity (lightweight semantic match — no extra installs)."
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

            with st.expander("Column mapping (we pre-fill best guesses — adjust if needed)", expanded=False):
                st.caption(
                    "We match your columns to a simple standard so costs roll up cleanly. "
                    "Leave a field blank if your file doesn’t have it."
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
                            st.success("Data saved. Continue to **Spending**.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Could not apply mapping: {e}")

        if st.session_state.get("using_example"):
            st.warning("No file upload — **using the example telecom dataset** so you can explore the flow.")

        st.stop()

    # Steps 2–4 require data
    if getattr(b_raw, "empty", True):
        st.error("Benchmark file is missing or empty. Complete Step 1.")
        st.stop()
    if w_raw.empty and f_raw.empty:
        st.error("Your tables look empty. Upload data in Step 1.")
        st.stop()

    result = run_filtered_analysis(w_raw, f_raw, b_raw, region, network)
    st.markdown("##### Summary")
    st.caption(
        f"<span style='color:{RISK_COLOR};font-weight:600;'>Red</span> = risk vs peers · "
        f"<span style='color:{OPP_COLOR};font-weight:600;'>Green</span> = opportunity / favorable in charts",
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

    if step == STEP_LABELS[1]:
        st.markdown("#### Step 2 · What are we spending?")
        st.caption("The big picture before any peer comparison.")

        dh = result.get("data_health") or {}
        st.markdown("##### Smart data layer · health")
        col_h, col_w = st.columns([1, 2])
        with col_h:
            sc = dh.get("data_health_score", "—")
            band = dh.get("data_health_band", "")
            st.metric("Data health score", f"{sc}/100", help="Missing values, outliers, taxonomy gaps, transport coverage.")
            st.caption(band or "")
        with col_w:
            for wmsg in dh.get("warnings", [])[:6]:
                st.warning(wmsg, icon="⚠️")

        with st.expander("Semantic metrics layer (definitions)", expanded=False):
            st.caption("Single source of truth for KPI formulas — extend in `metrics_layer.py`.")
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
            "Total annual network cost (in scope)",
            _usd(total),
            help=METRIC_HELP["total_cost"],
        )

        conc = top_concentration_phrase(base["category_shares"], top_n=2)
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
                title="How spend splits: wireless vs fiber",
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
                title="Where the money goes (share of total)",
                height=380,
                xaxis_title="Percent of total",
                margin=dict(t=50, b=20),
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("**So what?** Most programs land in labor, vendors, and backhaul — the next step shows how your mix compares.")

    elif step == STEP_LABELS[2]:
        st.markdown("#### Step 3 · How do we compare?")
        st.caption("Static peer medians plus **similar-peer** cohorts — red = higher than peers (risk), green = lower (favorable).")

        dyn = result.get("dynamic_peer_benchmark") or {}
        if dyn.get("narrative") and network != NETWORK_FIBER:
            peers_named = ", ".join(dyn.get("similar_peer_names") or [])
            st.info(f"**Dynamic benchmark:** {dyn['narrative']}")
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
                "Cost per site (wireless)",
                _usd(w["cost_per_site"]) if network != NETWORK_FIBER else "—",
                delta=f"{site_v:+.1f}% vs peers" if network != NETWORK_FIBER and site_v is not None else None,
                help=METRIC_HELP["cost_per_site"],
            )
        with metrics[1]:
            st.metric(
                "Cost per unit of traffic (wireless)",
                _usd(w["cost_per_tb"]) if network != NETWORK_FIBER else "—",
                delta=f"{tb_v:+.1f}% vs peers" if network != NETWORK_FIBER and tb_v is not None else None,
                help=METRIC_HELP["cost_per_tb"],
            )
        with metrics[2]:
            st.metric(
                "Cost per home passed (fiber)",
                _usd(f["cost_per_home_passed"]) if network != NETWORK_WIRELESS else "—",
                help="Annual fiber-related spend divided by homes passed.",
            )

        st.markdown("**So what?**")
        st.markdown(benchmark_plain_insight(var, idx))

        st.markdown("##### AI insight engine (prioritized)")
        ranked = result.get("ranked_insights") or []
        for card in ranked[:6]:
            sev = card.get("severity") or "watch"
            border = RISK_COLOR if sev == "risk" else (OPP_COLOR if sev == "opportunity" else NEUTRAL)
            st.markdown(
                f"<div style='border-left:4px solid {border};padding-left:12px;margin:10px 0;'>"
                f"<strong>{card.get('title','')}</strong><br/><span style='color:#334155;'>{card.get('body','')}</span></div>",
                unsafe_allow_html=True,
            )
            with st.expander(f"Why this insight? — {card.get('title', 'Detail')[:48]}"):
                st.write("**Drivers considered:** " + "; ".join(card.get("drivers") or []))
                st.write("**Data refs:** " + ", ".join(card.get("data_refs") or []))
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
                        "Nearest peers = smallest Euclidean distance in z-scored log(cost/site), operator type, "
                        "and density segment vs a profile inferred from your wireless/fiber mix."
                    )

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
                title="You vs peer median (wireless)",
                height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.05),
                margin=dict(t=60, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Red (you) above the gray peer bar means you spend more on that metric; green means you spend less."
            )

    elif step == STEP_LABELS[3]:
        st.markdown("#### Step 4 · What should we do?")
        st.caption("Prescriptive recommendations, collaboration workflow, scenarios, and chat — start with **Start here**.")

        lo, hi = opps["total_savings_range"]
        st.success(
            f"**Estimated savings range (illustrative):** {_usd(lo)} – {_usd(hi)} per year. "
            f"{METRIC_HELP['savings_range']}"
        )

        with st.expander("Executive story mode (slide-ready)", expanded=False):
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
            for f in story.get("findings", []):
                st.markdown(f"- {f}")
            st.markdown("**Top opportunities**")
            for o in story.get("opportunities", []):
                st.markdown(f"- {o}")
            st.markdown(f"**Estimated savings:** {story.get('estimated_savings', '')}")
            st.markdown(story.get("data_health", ""))
            st.caption(story.get("footer", ""))

        st.markdown("##### Opportunity simulation")
        st.caption("Adjust levers — impact updates in real time (category-level model).")
        s1, s2, s3 = st.columns(3)
        with s1:
            v_cut = st.slider("Vendor / third-party reduction %", 0, 25, 0, help="Applied to vendor taxonomy bucket.")
            l_prod = st.slider("Labor productivity gain %", 0, 25, 0, help="Modeled as effective labor cost reduction.")
        with s2:
            t_cut = st.slider("Transport / backhaul reduction %", 0, 25, 0)
            i_cut = st.slider("Infrastructure reduction %", 0, 20, 0)
        with s3:
            n_cut = st.slider("NetOps / O&M efficiency %", 0, 20, 0)
        scen = run_scenario(
            base,
            vendor_cost_reduction_pct=v_cut / 100.0,
            labor_productivity_pct=l_prod / 100.0,
            transport_reduction_pct=t_cut / 100.0,
            infrastructure_reduction_pct=i_cut / 100.0,
            netops_efficiency_pct=n_cut / 100.0,
        )
        st.metric(
            "Scenario savings (annual)",
            _usd(scen["total_savings_usd"]),
            help="Illustrative; see assumptions below.",
        )
        ex = scen["kpi_deltas"]["cost_per_site"]
        if ex["before"] > 0:
            st.caption(
                f"Wireless cost/site: {_usd(ex['before'])} → {_usd(ex['after'])} · "
                f"Cost/TB: {_usd(scen['kpi_deltas']['cost_per_tb']['before'])} → {_usd(scen['kpi_deltas']['cost_per_tb']['after'])}"
            )
        st.caption(scen.get("assumptions", ""))

        st.markdown("##### Recommendation engine")
        top = opps.get("top_5", [])[:5]
        for i, item in enumerate(top):
            title = item.get("business_title") or item.get("title")
            effort = item.get("effort", "Medium")
            lid = item.get("lever_id") or str(i)
            tag = ""
            if i < 2:
                tag = '<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:6px;font-size:0.8rem;font-weight:600;">Start here</span>'
            savings_txt = f"{_usd(item['savings_low_usd'])} – {_usd(item['savings_high_usd'])}"
            conf = item.get("confidence_0_100", "—")
            cx = item.get("complexity_tier", "Medium")
            tim = item.get("time_to_implement", "—")
            action = item.get("recommended_action", "")
            body = (
                f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:1rem 1.1rem;margin-bottom:0.75rem;background:#fff;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">'
                f'<div style="font-size:1.05rem;font-weight:600;color:#111827;">{title}</div>{tag}</div>'
                f'<div style="color:#475569;margin-top:0.35rem;">Estimated savings: <strong>{savings_txt}</strong> · '
                f'Effort: <strong>{effort}</strong> · Complexity: <strong>{cx}</strong> · '
                f'Time: <strong>{tim}</strong> · Confidence: <strong>{conf}/100</strong></div>'
                f'<div style="color:#334155;margin-top:0.5rem;font-size:0.95rem;">{action}</div></div>'
            )
            st.markdown(body, unsafe_allow_html=True)
            with st.expander(f"Explain · {title[:40]}"):
                exo = explain_opportunity(item, base)
                st.write(exo.get("summary", ""))
                for s in exo.get("steps", []):
                    st.caption(s)

        st.markdown("##### Workflow & collaboration")
        st.caption("Tag opportunities, assign owners, track status (session-local prototype).")
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

        st.markdown("##### Ask the co-pilot")
        st.caption('Examples: "Why are my costs higher?" · "Where is the biggest savings opportunity?"')
        for msg in st.session_state.chat_messages[-12:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        q = st.chat_input("Ask about this dataset…")
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
            "Optional: set `OPENAI_API_KEY` for richer LLM narratives in `insights.py` — rule-based paths work offline."
        )


if __name__ == "__main__":
    main()
