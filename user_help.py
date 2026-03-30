"""User-facing help content and in-app guide for the Network cost co-pilot."""
from __future__ import annotations

import pandas as pd
import streamlit as st


def render_user_guide() -> None:
    """Full help page (shown when user selects Help in the sidebar)."""
    st.markdown("# Help & user guide")
    st.caption(
        "How to use the Network cost co-pilot — from loading data to scenarios, chat, and exports of insights."
    )

    with st.expander("1 · Getting started", expanded=True):
        st.markdown(
            """
**What this app does**  
It turns wireless cost lines, fiber cost rollups, and a peer benchmark file into **KPIs**, **peer comparisons**, **prioritized insights**, **savings ideas**, and **what-if scenarios**.

**Two ways to load data**  
- **Example dataset:** On first visit, sample wireless, fiber, and benchmark files load automatically so you can explore all four steps.  
- **Your files:** On **Step 1 · Data**, upload three spreadsheets (CSV or Excel): wireless costs, fiber costs, and peer benchmarks. Confirm column mappings, then click **Use these files & mappings**.

**After Step 1**  
Use the horizontal **Guided steps** control to move through Spending → Comparison → Actions. A **progress bar** shows *Step N of 4*.
            """
        )

    with st.expander("2 · Step 1 — Bring your data"):
        st.markdown(
            """
**Required inputs**  
- **Wireless:** Site-level or line-level spend with amounts (mapped to **Amount_USD**). **Site_ID** and a description column improve rollups and taxonomy.  
- **Fiber:** Wide columns for labor, transport, build, etc. (see mapping screen for canonical names).  
- **Benchmarks:** Peer rows with category shares and, when available, **Cost_per_site_USD** and **Cost_per_TB_USD**.

**Column mapping**  
The app suggests columns from name patterns. Adjust dropdowns if a guess is wrong. **Amount_USD** on wireless is required to proceed.

**Semantic auto-mapping (hints)**  
Open **Auto-mapping (semantic similarity)** to see how each source column ranks against standard fields. Use it as a **second opinion**, not a substitute for your business judgment.

**Data health**  
After data is loaded, **Step 2** shows a **Data health score** and warnings (missing values, outliers, transport coverage). Improve the score by fixing extracts and mappings.
            """
        )

    with st.expander("3 · Filters (area & network)"):
        st.markdown(
            """
From **Step 2** onward, you can narrow the analysis:

- **Area focus:** All areas, Metro & suburban, or Rural (uses a **Density**-like column on wireless when present).  
- **Network focus:** Wireless + fiber combined, Wireless only, or Fiber only.

Changing filters **re-runs** the analysis (cached for speed). Some wireless-only KPIs are hidden when you choose **Fiber only**.
            """
        )

    with st.expander("4 · Step 2 — Spending & semantic metrics"):
        st.markdown(
            """
**Summary strip**  
At the top: **Data health**, **vs peer median**, **vs similar peers**, and **modeled savings range** (illustrative).

**Charts**  
Wireless vs fiber mix and **share of spend** by standard category (labor, vendor, transport, etc.).

**Semantic metrics layer**  
Expand **Semantic metrics layer** to see **definitions and formulas** for KPIs (cost per site, cost per TB, labor ratio, …). Analysts can extend definitions in code (`metrics_layer.py`) so the whole app stays consistent.
            """
        )

    with st.expander("5 · Step 3 — Comparison & AI insights"):
        st.markdown(
            """
**Peer median**  
Compares your wireless **cost per site** and **cost per TB** to the **median** of peers in the benchmark file.

**Dynamic benchmark (similar peers)**  
The app picks a small cohort of **most similar peers** (scale, operator type, density) and compares you to **their** median — not one global average. Read the blue info callout for the narrative.

**Colors**  
**Red** in charts usually means **higher than peers** (cost risk). **Green** means **lower** (favorable). The summary area explains this explicitly.

**Prioritized insights**  
Insights are **ordered by impact**. Open **Why this insight?** to see **drivers**, **data references**, and **calculation steps** (explainability).

**Trust**  
All numeric answers come from **your tables and the benchmark file**. Optional OpenAI (see below) only enriches long-form narrative text where enabled.
            """
        )

    with st.expander("6 · Step 4 — Actions, simulation & workflow"):
        st.markdown(
            """
**Executive story mode**  
One place for **three findings**, **three opportunities**, **estimated savings**, and **data health** — suitable to copy into slides or email.

**Opportunity simulation**  
Move sliders for **vendor reduction**, **labor productivity**, **transport**, **infrastructure**, and **netops**. The app shows **estimated annual savings** and **before/after KPIs** using a simple category-level model (read the **assumptions** caption).

**Recommendations**  
Each idea includes **estimated savings range**, **effort**, **complexity**, **time to implement**, **confidence score**, and a **recommended action**. Use **Explain** for how savings were derived.

**Workflow (collaboration)**  
Assign **tags**, **owner**, and **status** (Not started / In progress / Done). Stored in your **browser session** — refresh clears it; use for working sessions or demos.

**Ask the co-pilot (chat)**  
Type questions such as:  
- *Why are my costs higher?*  
- *Where is the biggest savings opportunity?*  
- *How does backhaul compare?*  

Answers use **rules** over your current results (no API key required). Chat history is kept for the session (last messages shown).
            """
        )

    with st.expander("7 · Optional: OpenAI (longer narratives)"):
        st.markdown(
            """
If you set the environment variable **`OPENAI_API_KEY`**, the app can generate **longer narrative insights** in some code paths (`insights.py`).  
**The app is fully usable without it** — benchmarks, metrics, simulation, chat, and explainability work offline.
            """
        )

    with st.expander("8 · Tips for reliable results"):
        st.markdown(
            """
- Use **consistent units** (e.g. annual USD) across wireless and fiber.  
- Keep **peer benchmark** categories aligned with the app taxonomy where possible.  
- If **Data health** warns about missing **transport** lines, check **Cost_Line_Description** mapping to taxonomy.  
- Treat **savings ranges** and **simulation** as **directional** — validate with finance and engineering before commitments.  
- For **large files** (thousands of rows), uploads are fine; very heavy ETL may need a database or notebook in a future version.
            """
        )

    st.divider()
    st.markdown("### Quick reference — guided steps")
    st.dataframe(
        pd.DataFrame(
            {
                "Step": ["1 · Data", "2 · Spending", "3 · Comparison", "4 · Actions"],
                "You do": [
                    "Upload or use example data; map columns",
                    "Review health, totals, and category mix",
                    "Read peer vs similar-peer insights",
                    "Run scenarios, assign work, ask the co-pilot",
                ],
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.divider()
    st.caption("Created by **Nigel Biggs**")


def render_sidebar_help_teaser() -> None:
    """Short hints in the sidebar when user is in Analysis view."""
    with st.expander("Quick tips", expanded=False):
        st.markdown(
            """
- **Step 1:** Map **Amount_USD** for wireless.  
- **Step 3:** Open **Why this insight?** for transparency.  
- **Step 4:** Try **simulation** sliders and **Executive story mode**.  
- Switch to **Help & instructions** above for the full guide.
            """
        )
