# Database Setup — JobPulse AI

This folder contains PostgreSQL scripts for the `jobpulse_db` database.

## Files

| File            | Description                                                        |
|-----------------|--------------------------------------------------------------------|
| `schema.sql`    | Creates the `jobs`, `skills`, and `job_skills` tables with indexes |
| `seed_data.sql` | Inserts the canonical skill dictionary into the `skills` table     |
| `queries.sql`   | 15 analytical business queries (top skills, salaries, trends, etc.)|

## Setup Steps

1. Install PostgreSQL and ensure the service is running.

2. Create the database (one time):

```sql
CREATE DATABASE jobpulse_db;
```

3. Apply the schema:

```bash
psql -U postgres -d jobpulse_db -f database/schema.sql
```

4. Load seed data:

```bash
psql -U postgres -d jobpulse_db -f database/seed_data.sql
```

5. Set environment variables in a `.env` file (see `.env.example`):

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jobpulse_db
DB_USER=postgres
DB_PASSWORD=your_password
```

6. Run the full pipeline to load job data:

```bash
python scripts/run_pipeline.py
```

## Quick Alternative

`scripts/setup_database.py` automates steps 3 + 4 using SQLAlchemy.
See the script README for details.

## Connection via `.env`

The application reads connection details from your `.env` file.
Never commit the `.env` file to GitHub (it is in `.gitignore`).