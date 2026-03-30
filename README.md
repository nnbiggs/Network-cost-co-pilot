# PwC One — Network Cost Intelligence

A **PwC One-powered Network Cost Intelligence** experience for telecom clients: **AI-assisted** ingestion and benchmarking, **traceable** peer comparison, **quantified savings opportunities**, and a **prioritized action roadmap** — with **PwC professional judgment** framing throughout.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Bundled sample wireless, fiber, and benchmark files under `data/` support **executive-ready demos** without client data.

The **PwC logo** is loaded from `assets/pwc_logo.svg` (see `assets/README.md` for source and trademark note). Replace that file with your official brand asset if required.

---

## Deploy (Vercel + Streamlit)

**Vercel cannot run Streamlit** (it needs a long-lived Python process and WebSockets). This repo is set up so **Vercel** hosts a **branded landing page** that links to the app hosted on **Streamlit Community Cloud** (or any URL you choose).

### 1) Host the Streamlit app

1. Push this repo to GitHub (if it is not already).
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/) and **New app** → connect the repo.
3. Set **Main file path** to `app.py`.
4. Deploy and copy the app URL (e.g. `https://your-app.streamlit.app`).

### 2) Connect your existing Vercel project

1. Import or open the **same GitHub repo** in Vercel (project you already have).
2. **Settings → Environment Variables** → add:
   - **Name:** `STREAMLIT_APP_URL`
   - **Value:** your Streamlit URL (e.g. `https://your-app.streamlit.app`)
3. **Settings → General** → confirm **Build & Development**:
   - **Framework Preset:** Other (or leave auto; `vercel.json` drives the build).
   - Build uses `npm run build` and outputs the `out/` folder per `vercel.json`.
4. Redeploy. The site will show the landing page; **Launch application** uses `STREAMLIT_APP_URL`.

Local check: `npm run build` → open `out/index.html`.

If Vercel tries to run a **Python** install from `requirements.txt` and conflicts, set **Install Command** in the Vercel project to `npm install` only (or leave default; `vercel.json` should override with `installCommand`).

---

## Live demo talk track (partner / executive narrative)

Use this sequence while clicking through the guided phases:

1. **Set the frame**  
   “This is **PwC One applied to network cost optimization** — not a static report. We compress a traditional diagnostic: **faster ingestion**, **smarter benchmarking**, and **clearer actions** in one workspace.”

2. **Overview**  
   “Here is the **executive overview**: **cost position vs peers**, the **lead optimization lever**, a **modeled savings range**, and **priority actions** suitable for a steering committee. Everything traces back to your data and benchmark file.”

3. **Ingest & standardize**  
   “Client cost data arrives **fragmented**. PwC One **assists** with intelligent field mapping into a **common network cost taxonomy** — labor, vendor, backhaul, infrastructure, operations. Teams still apply **PwC judgment** to confirm mappings. You see **data quality** and **mapping confidence** on the baseline view.”

4. **Integrated cost baseline**  
   “This is the **fact-based integrated baseline** across **wireless and fiber** — where the money goes in **business language**, not GL codes.”

5. **Peer benchmark comparison**  
   “We compare to **peer medians** and to a **similar-peer cohort** so the story is **tailored**, not a single generic average. Red and green make **cost pressure vs favorable position** obvious.”

6. **AI-assisted gap insights**  
   “**AI accelerates** root-cause pattern detection; **PwC validates** the narrative. Each insight shows **why it matters**, **what data supports it**, and a **suggested action** — with **Why this insight?** for full traceability.”

7. **Prioritized action roadmap**  
   “We translate insights into **quantified savings opportunities**, **sequencing** — quick wins through longer-cycle — **scenario modeling**, and a **natural-language** Q&A layer. The export block is formatted for **steering** and follow-up workshops.”

8. **Trust close**  
   “**AI-assisted cost intelligence** plus **PwC judgment**: faster from **data** to **decision** to **execution**, with an audit trail clients can defend.”

---

## Architecture (modular)

| Module | Role |
|--------|------|
| `app.py` | PwC One UX, guided phases, executive panels |
| `pwc_experience.py` | Positioning copy, storyline, executive panel payload |
| `pipeline.py` | Ingest → normalize → baseline → benchmark → opportunities |
| `data_health.py` | Data quality score + mapping confidence |
| `insight_engine.py` | Consultant-style insight narratives + Q&A framing |
| `benchmarking.py` | Peer median + similar-peer clustering |
| `opportunities.py` | Quantified levers, PwC category tags, roadmap inputs |
| `semantic_mapping.py` | AI-assisted column alignment hints |

---

## Optional

Set `OPENAI_API_KEY` to enrich long-form narrative generation in `insights.py`. The application runs fully with **rule-based**, traceable outputs without it.

---

*Experience created by Nigel Biggs.*
