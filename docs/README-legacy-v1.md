# JobPulse AI

**Job Market & Skills Intelligence Platform**

> "Understand the Job Market. Discover Your Skill Gap. Build Your Career."

🚀 **Live Demo:** [Streamlit Community Cloud](https://share.streamlit.io/) — see
[Deployment](#deployment-streamlit-community-cloud) below for the one-click setup.

---

## Table of Contents

1. [Project Description](#project-description)
2. [Business Problem](#business-problem)
3. [Solution](#solution)
4. [Key Features](#key-features)
5. [Technology Stack](#technology-stack)
6. [Project Architecture](#project-architecture)
7. [Folder Structure](#folder-structure)
8. [Dataset](#dataset)
9. [Installation](#installation)
10. [Environment Setup](#environment-setup)
11. [PostgreSQL Setup](#postgresql-setup)
12. [Running the Data Pipeline](#running-the-data-pipeline)
13. [Launching Streamlit](#launching-streamlit)
14. [Running Tests](#running-tests)
15. [Dashboard Pages](#dashboard-pages)
16. [AI Features](#ai-features)
17. [Key Insights](#key-insights)
18. [Screenshots](#screenshots)
19. [Power BI](#power-bi)
20. [Future Improvements](#future-improvements)
21. [Author](#author)
22. [Deployment](#deployment-streamlit-community-cloud)

---

## Project Description

JobPulse AI is a complete end-to-end data analytics project that analyses
**job market data** to deliver actionable intelligence about:

- Job market demand by role, location, and industry
- Most in-demand technical skills
- Top hiring companies
- Salary trends by role, experience, and location
- Skill combinations requested together
- Personalized **career readiness scores**
- Data-driven **learning recommendations**
- **Job recommendations** matched to a user's skills

The platform initially focuses on the **Indian job market** for seven target
roles: Data Analyst, Business Analyst, Data Scientist, Data Engineer,
Machine Learning Engineer, BI Analyst, and Analytics Engineer.

---

## Business Problem

Job seekers often struggle to answer critical career questions:

- *Which skills should I learn to get hired as a Data Analyst?*
- *How does my current skill set compare to market demand?*
- *Which cities pay the most for my role?*
- *Which companies are hiring the most?*
- *What is my career readiness score, and how do I improve it?*

Traditional job portals show raw listings but do **not** convert them into
actionable career intelligence. JobPulse AI solves this by turning raw job
posting data into market insights and personalized recommendations.

---

## Solution

JobPulse AI provides:

1. **Automated ETL pipeline** — load, validate, clean, and enrich job data
2. **Skill extraction engine** — maps raw skill mentions to canonical skills
3. **PostgreSQL data warehouse** — structured relational storage
4. **Interactive Streamlit dashboard** — dynamic market exploration
5. **AI-powered career tools** — readiness scores and job recommendations
6. **Power BI-ready exports** — processed CSVs for external BI tools

---

## Key Features

| Feature | Description |
|---------|-------------|
| Market Insights | Jobs by role, location, industry, and time |
| Skills Intelligence | Top skills, categories, combos, role comparison |
| Salary Explorer | Salary distribution by role/location/experience |
| Company Insights | Hiring profiles based on dataset only |
| Career Advisor | Skill-gap analysis & readiness score |
| Job Recommendations | TF-IDF + cosine similarity matching |
| Salary Prediction | ML model (Random Forest / Gradient Boosting) |
| Power BI Exports | Ready-to-import CSV files |
## Technology Stack

- **Language:** Python 3.11+
- **Data processing:** Pandas, NumPy
- **Database:** PostgreSQL (SQLAlchemy, psycopg2)
- **Machine Learning:** Scikit-learn (TF-IDF, Random Forest)
- **Visualization:** Plotly, Matplotlib, Seaborn
- **Dashboard:** Streamlit
- **Testing:** Pytest

---

## Project Architecture

```
Raw Job Data
    ↓
Data Validation
    ↓
Data Cleaning
    ↓
Feature Engineering
    ↓
Skill Extraction Engine
    ↓
PostgreSQL Database
    ↓
SQL Analytics Layer
    ↓
Analytics Processing
    ↓
Streamlit Dashboard
    ↓
Skill Gap Analysis → Learning Recommendations
    ↓
Job Recommendation Engine → Career Insights
```

---

## Folder Structure

```
jobpulse-ai/
├── data/
│   ├── raw/            # Raw CSV input
│   ├── cleaned/        # Intermediate cleaned data
│   └── processed/      # Final processed + Power BI exports
├── database/
│   ├── schema.sql      # PostgreSQL schema
│   ├── queries.sql     # 15 analytical queries
│   └── seed_data.sql   # Skill dictionary seed
├── notebooks/          # Jupyter EDA notebooks
├── src/                # Core pipeline modules
├── models/             # ML models (skill gap, recommender, salary)
├── dashboard/          # Streamlit app + pages + components
├── reports/            # Business insights & data dictionary
├── tests/              # Pytest test suite
├── scripts/            # Pipeline, setup, generators
├── .env.example        # Environment template
├── requirements.txt
└── run.py              # CLI entry point
```

---

## Dataset

The project supports a CSV of job postings with columns such as
`job_id`, `job_title`, `company`, `location`, `city`, `state`, `country`,
`industry`, `salary`, `experience`, `posting_date`, `job_description`,
and `skills`. The pipeline handles missing columns gracefully.

**Sample data:** A synthetic generator (`scripts/generate_sample_data.py`)
creates **10,000+ realistic job postings** covering Indian cities and 8
industries. All sample data is **clearly labelled as synthetic** and is
intended for demonstration/portfolio purposes only.

---

## Installation

### 1. Clone / download the repository

```bash
git clone https://github.com/<your-username>/jobpulse-ai.git
cd jobpulse-ai
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:
- **Windows:** `venv\Scripts\activate`
- **macOS / Linux:** `source venv/bin/activate`

```bash
pip install -r requirements.txt

# Optional — for running tests & notebooks locally:
pip install -r requirements-dev.txt
```

---

## Environment Setup

Copy `.env.example` to `.env` and set your values:

```bash
cp .env.example .env
```

`.env` contents:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jobpulse_db
DB_USER=postgres
DB_PASSWORD=your_password
DATA_PATH=data/raw/jobs.csv
```

> Never commit `.env` — it is already in `.gitignore`.

---

## PostgreSQL Setup

1. Install and start PostgreSQL.
2. Create the database:
   ```bash
   psql -U postgres -c "CREATE DATABASE jobpulse_db;"
   ```
3. Apply schema and seed data:
   ```bash
   psql -U postgres -d jobpulse_db -f database/schema.sql
   psql -U postgres -d jobpulse_db -f database/seed_data.sql
   ```
   **Or** run the automated setup:
   ```bash
   python scripts/setup_database.py
   ```

---

## Running the Data Pipeline

### 1. Generate sample data (optional — if you have no dataset)

```bash
python scripts/generate_sample_data.py --records 10000
```

### 2. Run the full pipeline

```bash
python scripts/run_pipeline.py
```

Printed progress:

```
[1/9] Loading raw data...
[2/9] Validating data...
[3/9] Cleaning data...
[4/9] Extracting skills...
[5/9] Feature engineering...
[6/9] Saving processed data...
[7/9] Loading database...
[8/9] Generating analytics summaries...
[9/9] Generating business insights report...
```

To skip the database step:

```bash
python scripts/run_pipeline.py --skip-db
```

---

## Launching Streamlit

```bash
streamlit run dashboard/app.py
```

Or use the unified launcher:

```bash
python run.py
```

Then choose **option 4** from the menu.

---

## Running Tests

```bash
# Dev dependencies required (installs pytest + jupyter):
pip install -r requirements-dev.txt

pytest tests/ -v
```
## Dashboard Pages

| Page | Purpose |
|------|---------|
| **Home** | KPIs, market overview, trends |
| **Market Insights** | Filterable role/location/industry/date analysis |
| **Skills Intelligence** | Top skills, combos, role comparison |
| **Salary Explorer** | Salary by role/location/experience |
| **Company Insights** | Company hiring profiles |
| **Career Advisor** | Skill-gap analysis & readiness score |
| **Job Recommendations** | Personalised job matching |

---

## AI Features

### Career Advisor
- Weighted readiness score (`Critical` skills count more)
- Matched vs. missing skills breakdown
- Learning priority ranked by market demand

### Job Recommender
- TF-IDF vectorized job profiles
- Cosine similarity + skill/location/role/experience matching
- Match percentage and missing-skills reporting

### Salary Prediction
- Random Forest / Gradient Boosting regressor
- MAE, RMSE, R² evaluation metrics
- Gracefully disables if salary data is insufficient

---

## Key Insights

> All insights are generated dynamically from the loaded dataset — see
> `reports/business_insights.md` after running the pipeline.

Typical patterns visible in the sample data:

- **Bangalore / Hyderabad** lead job posting volumes
- **Python & SQL** dominate skill demand across roles
- **Data Engineer / MLE** roles show the highest average salaries
- **Power BI + SQL + Excel** is the core Data Analyst stack
- Scikit-learn, TensorFlow, and PyTorch lead ML skill demand

---

## Screenshots

> 📸 *Screenshots will be added here once the dashboard is running locally.*

Run `streamlit run dashboard/app.py` and capture:
1. Home page (KPI cards + overview charts)
2. Market Insights (filters + charts)
3. Career Advisor (readiness score)
4. Job Recommendations (match results)

---

## Power BI

Processed CSVs are exported automatically to `data/processed/`:
- `jobs_processed.csv`
- `skills_summary.csv`
- `company_summary.csv`
- `location_summary.csv`
- `salary_summary.csv`

Suggested Power BI pages:
1. **Executive Overview** — KPIs, trend lines
2. **Job Market Analysis** — role/location/industry breakdowns
3. **Skills Intelligence** — top skills, combos
4. **Salary Intelligence** — salary by role/location
5. **Company Intelligence** — company hiring profiles
6. **Career Insights** — readiness & skill-gap (mock)

Export manually any time:

```bash
python scripts/export_powerbi.py
```

---

## Deployment (Streamlit Community Cloud)

The app deploys free on [Streamlit Community Cloud](https://share.streamlit.io/)
directly from this repository — no Docker or server required.

1. Fork or clone this repo to your GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
3. Click **Create app** → **Deploy a public app from GitHub**.
4. Fill in:
   - **Repository:** `ankitkumaranalytics/Job-pulse-AI`
   - **Branch:** `main`
   - **Main file path:** `dashboard/app.py`
5. Click **Deploy**. First build takes a few minutes (dependencies install
   automatically from `requirements.txt`).

Notes:

- The sample dataset (`data/raw/jobs.csv`, `data/processed/*.csv`) is committed,
  so the deployed dashboard works out of the box — no database needed.
- Streamlit Community Cloud has no PostgreSQL server; the dashboard reads the
  processed CSVs. The database layer is for local/full-pipeline use.
- To redeploy after changes: just `git push` — the cloud app reboots
  automatically.

<details>
<summary>Alternative: deploy on Hugging Face Spaces</summary>

1. Create a new **Space** → SDK: **Streamlit**.
2. Push this repo to the Space (or upload files).
3. Add `dashboard/app.py` as the app path in `README.md` of the Space
   (`app_file: dashboard/app.py` in the YAML header).
</details>

---

## Future Improvements

- [ ] Real job data ingestion (APIs: Adzuna, Naukri, LinkedIn)
- [ ] Multi-country support (beyond India)
- [ ] Automated daily/weekly pipeline runs (Apache Airflow)
- [ ] NLP-based skill extraction improvements (spaCy)
- [ ] Salary prediction deployment endpoint (FastAPI)
- [ ] Dockerized PostgreSQL + Streamlit deployment

---

## Author

Built as a full-stack data analytics portfolio project.

**Tech skills demonstrated:** Data Engineering · Data Analysis ·
ETL Pipelines · PostgreSQL · Python · Machine Learning · BI Dashboards ·
Streamlit · Power BI preparation

---

*© JobPulse AI — Portfolio project. Sample data is synthetic unless stated otherwise.*