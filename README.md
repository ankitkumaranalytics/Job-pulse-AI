# Job Pulse AI

**AI-Powered Career Intelligence Platform**

Job Pulse AI is a production-style Streamlit application that turns a raw
job-postings dataset into a complete career toolkit: semantic job search,
hybrid job recommendations, resume/ATS intelligence, resume-to-job match
scoring, skill-gap analysis, personalised learning roadmaps, market
intelligence, an application tracker with funnel analytics, a mock
interview coach, and in-app smart alerts.

> Every score in the platform is **deterministic and explainable** — each
> component displays the exact factors that produced it. Heuristic scores
> are clearly labelled as heuristics, never presented as ML predictions.

---

## Features

| # | Feature | What it does |
|---|---------|--------------|
| 1 | **Resume Intelligence** | Upload PDF/DOCX/TXT, structured parsing (contact, skills, education, experience, projects, certifications) + transparent 0-100 ATS score with 5 weighted categories |
| 2 | **AI Job Match Engine** | Resume vs job-description matching across 6 components: skills, keywords, semantic similarity, experience, education, project relevance |
| 3 | **Job Recommendation Engine** | Hybrid engine (content-based + skill similarity + semantic + preference + demand) with a plain-language "Why this was recommended" on every card |
| 4 | **Semantic Job Search** | Natural-language queries ("fresher data analyst internship in Chennai with Python") parsed into intent (role, skills, location, level, type), then ranked results with keyword fallback |
| 5 | **Skill Gap Analysis** | Role requirements mined from real postings; priority = posting frequency x importance x foundational value, bucketed High/Medium/Low |
| 6 | **Career Roadmap** | Phased learning plan (Foundation, SQL, Programming, Visualization, Advanced, Cloud, Portfolio) with durations and progress tracking |
| 7 | **Market Intelligence** | Trends, location/industry/company analysis plus *actionable* insight sentences that cite the underlying numbers |
| 8 | **Application Tracker** | SQLite persistence (Saved, Applied, Assessment, Interview, Offer, Rejected) with interview/response/offer rates |
| 9 | **Interview Coach** | Role/type-specific question generation (seeded, reproducible) + heuristic answer evaluation (technical, communication, STAR structure, completeness) |
| 10 | **Application Strength Estimator** | Alignment-based strength score — explicitly *not* a hiring prediction |
| 11 | **Smart Alerts** | In-app notifications: high-match opportunities, missing-skill bridges, follow-up reminders, profile-completeness nudges |

---

## Architecture

```
jobpulse-ai/
├── dashboard/
│   ├── app.py                  # Entry point: navigation + page dispatch
│   ├── pages/                  # 11 thin UI pages (render only)
│   │   ├── home.py             ├── job_search.py
│   │   ├── job_recommendations ├── resume_intelligence.py
│   │   ├── career_advisor.py   ├── interview_coach.py
│   │   ├── application_tracker ├── market_insights.py
│   │   ├── skills_intelligence ├── salary_explorer.py
│   │   └── company_insights.py
│   ├── services/               # Business + AI logic (pure, testable cores)
│   │   ├── resume_service.py   ├── ats_service.py
│   │   ├── match_service.py    ├── recommendation_service.py
│   │   ├── search_service.py   ├── skill_gap_service.py
│   │   ├── roadmap_service.py  ├── interview_service.py
│   │   ├── tracker_service.py  ├── alerts_service.py
│   │   └── market_service.py
│   ├── models/                 # Typed entities (Job, ResumeProfile, UserProfile, Application)
│   ├── components/             # premium UI kit, styling, charts, upload, filters, sidebar
│   └── utils/                  # constants, scoring, text_processing, validation
├── models/                     # Pre-existing ML models (skill gap, recommender, salary)
├── src/                        # Data pipeline, analytics, skill dictionary, DB access
├── data/                       # raw -> cleaned -> processed CSVs + SQLite tracker DB
├── tests/                      # 81 tests (services + dashboard integration)
├── scripts/, notebooks/, database/, reports/, docs/
└── requirements.txt
```

**Layering rule:** Streamlit pages render; services compute. Pure service
cores import no Streamlit, which keeps every algorithm unit-testable.
Expensive artefacts (TF-IDF corpora, models) are cached with
`@st.cache_resource` / `@st.cache_data`.

## Technology Stack

Python 3.11-3.13 · Streamlit · Pandas · NumPy · scikit-learn (TF-IDF,
cosine similarity) · Plotly · SQLite (tracker) · PostgreSQL/SQLAlchemy
(optional job source) · pypdf + python-docx (resume parsing) · pytest.

## AI / Scoring Explained

- **ATS Score** = 30% skills coverage + 25% keyword optimisation + 20%
  experience relevance + 15% structure checklist + 10% project strength,
  computed against role requirements mined from real postings.
- **Match Score** = 30% skills + 20% keywords + 20% semantic + 15%
  experience + 10% education + 5% projects.
- **Semantic similarity** = TF-IDF word (1-2 g) + character (3-5 g) cosine
  blend, calibrated so strong topical alignment reads as a strong score.
  Set `JOBPULSE_USE_EMBEDDINGS=true` with `sentence-transformers`
  installed for true embeddings (automatic fallback if unavailable).
- **Recommendations** = 40% skill similarity + 25% semantic + 20%
  preference (role/location/experience) + 15% market demand.
- **Skill-gap priority** = 45% posting frequency + 35% importance
  (Critical > Important > Optional) + 20% foundational boost.
- **Interview evaluation** = 35% technical coverage + 25% communication
  (length bands, filler detection) + 20% STAR structure + 20% completeness.

All outputs pass through a `clamp100` guard — the test suite asserts
`0 <= score <= 100` everywhere. These are **heuristics and
information-retrieval techniques**, not trained models; the UI labels
them as such in every relevant view.

## Installation

```bash
git clone https://github.com/ankitkumaranalytics/Job-pulse-AI.git
cd Job-pulse-AI
pip install -r requirements.txt
```

Optional true-embedding engine:

```bash
pip install sentence-transformers   # then set JOBPULSE_USE_EMBEDDINGS=true
```

## Environment Setup

Copy `.env.example` to `.env` (all keys optional — the app runs with zero
configuration on CSV fallback):

| Key | Purpose |
|-----|---------|
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_ENABLED` | PostgreSQL job source (falls back to CSV when absent) |
| `JOBPULSE_TRACKER_DB` | SQLite path for the tracker (default `data/jobpulse_tracker.db`) |
| `JOBPULSE_USE_EMBEDDINGS` | `true` enables sentence-transformers semantic engine |
| `DATA_PATH`, `DATA_OUTPUT_DIR` | Data pipeline paths |

Never commit real credentials; on Streamlit Cloud use **Secrets** instead
of `.env`.

## How to Run

```bash
streamlit run dashboard/app.py
# or: python run.py
```

Regenerate the dataset first if needed:

```bash
python scripts/generate_sample_data.py
python scripts/run_pipeline.py --skip-db
```

## Running Tests

```bash
python -m pytest tests/ -q
```

81 tests: service-layer units (parsing, scoring bounds, ranking,
persistence) plus full-app integration tests (every page renders, CTA
navigation, session-state safety).

## Deployment (Streamlit Community Cloud)

- Deploy `dashboard/app.py`; add DB credentials under **Secrets** if used.
- The tracker's SQLite file lives on an **ephemeral** filesystem — entries
  reset on redeploy/restart. Point `JOBPULSE_TRACKER_DB` at a mounted
  volume, or wire the tracker to PostgreSQL for durable storage.
- `sentence-transformers` is intentionally excluded from requirements.txt
  to keep Cloud builds fast; the TF-IDF fallback keeps every feature
  functional without it.

## Screenshots

_(placeholder — add screenshots of Overview, Job Search, Resume
Intelligence, Interview Coach and Application Tracker here)_

## Limitations

- The bundled dataset is synthetic demo data; swap in a live feed for
  production use.
- The ATS score is a simulation — real vendor ATS behaviour varies.
- The default semantic engine is lexical (TF-IDF); embeddings are opt-in.
- Tracker persistence is local and ephemeral on Community Cloud.
- Interview feedback is heuristic guidance, not professional assessment.

## Future Improvements

- Live job ingestion (per-board adapters) with scheduled refresh.
- PostgreSQL-backed tracker with per-user authentication.
- Embedding index (FAISS/Chroma) with incremental updates.
- LLM-generated interview follow-ups behind strict guardrails with
  deterministic fallbacks.
- Saved-profile persistence and multi-resume comparison.
- Accessibility (WCAG AA) and internationalisation passes.

---

Legacy documentation for the v1 data-platform-only iteration is preserved
at `docs/README-legacy-v1.md`.
