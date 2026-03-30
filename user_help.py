"""User guide — PwC One Network Cost Intelligence."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

_LOGO = Path(__file__).resolve().parent / "assets" / "pwc_logo.svg"


def render_user_guide() -> None:
    if _LOGO.exists():
        st.image(str(_LOGO), width=140)
    st.markdown("# Help & user guide")
    st.caption(
        "**PwC One — Network Cost Intelligence:** how to run the guided experience from ingestion through prioritized roadmap."
    )

    with st.expander("1 · Positioning & storyline", expanded=True):
        st.markdown(
            """
This application demonstrates **PwC One applied to network cost optimization**: a **secure client workspace** design intent, 
**AI-assisted** data ingestion and normalization, **PwC professional oversight** in how insights are framed, and 
**traceable, action-oriented** outputs — **faster from data to decision to execution**.

**Compression message**  
PwC One **compresses a traditional diagnostic**: faster ingestion, smarter benchmarking (including **similar-peer** views), 
and **quantified savings opportunities** with a **prioritized action roadmap** for leadership.
            """
        )

    with st.expander("2 · Guided phases (what to click)", expanded=False):
        st.markdown(
            """
| Phase | Purpose |
|--------|---------|
| **Overview** | Executive summary: cost gap vs peers, lead lever, savings range, priority actions |
| **Ingest & standardize** | Upload or example data; AI-assisted mapping to **PwC network cost taxonomy** |
| **Integrated cost baseline** | Where spend sits — wireless vs fiber and business cost categories |
| **Peer benchmark comparison** | Headline KPIs vs **peer median**; tailored **similar-peer** narrative |
| **AI-assisted gap insights** | Root-cause style observations with **why / data / action** |
| **Prioritized action roadmap** | Sequencing, scenarios, categorized opportunities, NL Q&A |

Use **Geography** and **Network** scope from the baseline phase onward to narrow the view.
            """
        )

    with st.expander("3 · Ingest & data quality", expanded=False):
        st.markdown(
            """
**Drag and drop** or browse CSV/Excel for wireless, fiber, and peer benchmark files — or use **Use example telecom dataset**.

**Mapping confidence** and **data quality score** reflect field coverage, outliers, and taxonomy mapping strength. 
**PwC teams** validate mappings on live engagements.

**Required for wireless:** map an amount column to **Amount_USD**.
            """
        )

    with st.expander("4 · Trust & explainability", expanded=False):
        st.markdown(
            """
**AI accelerates analysis; PwC judgment validates.** Open **Why this insight?** and **Traceability** expanders to see 
underlying data references and calculation logic.

**Quantified savings** and **scenarios** are **modeled ranges** for discussion — finance and network teams should 
confirm before commitments.
            """
        )

    with st.expander("5 · Optional OpenAI", expanded=False):
        st.markdown(
            """
Setting **`OPENAI_API_KEY`** can deepen narrative text in some modules. The experience is **fully functional** without it, 
using deterministic, traceable intelligence.
            """
        )

    st.divider()
    st.dataframe(
        pd.DataFrame(
            {
                "Phase": [
                    "Overview",
                    "Ingest & standardize",
                    "Integrated cost baseline",
                    "Peer benchmark comparison",
                    "AI-assisted gap insights",
                    "Prioritized action roadmap",
                ],
                "Audience outcome": [
                    "Steering-ready headline panel",
                    "Standardized client cost model",
                    "Fact-based spend picture",
                    "Credible peer positioning",
                    "Consultant-grade gap narrative",
                    "Execution sequencing & scenarios",
                ],
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.divider()
    st.caption("Created by **Nigel Biggs**")


def render_sidebar_help_teaser() -> None:
    with st.expander("Quick tips", expanded=False):
        st.markdown(
            """
- Start at **Overview** for the executive storyline.  
- **Ingest & standardize** — confirm **Amount_USD** mapping.  
- **AI-assisted gap insights** — use **Why this insight?** for traceability.  
- **Prioritized action roadmap** — quick wins vs longer-cycle columns.  
- Full guide: **Help & instructions**.
            """
        )
