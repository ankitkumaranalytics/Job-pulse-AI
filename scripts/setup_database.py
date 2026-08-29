"""
Setup the PostgreSQL database for JobPulse AI.

Creates the database jobpulse_db (if not exists), applies the schema,
and loads the seed skill dictionary.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import logger, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from src import database_loader


def setup_database(auto_create: bool = True) -> bool:
    """
    Run the database setup steps.

    Parameters
    ----------
    auto_create : bool
        If True, attempt to create the database if it does not exist.

    Returns
    -------
    bool
        True if setup succeeded.
    """
    print("=" * 60)
    print("JobPulse AI - Database Setup")
    print("=" * 60)
    print(f"Host: {DB_HOST}:{DB_PORT}")
    print(f"Database: {DB_NAME}")
    print(f"User: {DB_USER}")
    print()

    # Step 1: Test connection
    print("[1/3] Testing database connection...")
    if database_loader.test_connection():
        print("  Connection OK")
    else:
        if not auto_create:
            print("  Could not connect. Set correct credentials in .env")
            return False
        # Try to create the database
        print("  Could not connect to jobpulse_db - attempting to create it...")
        try:
            create_database()
        except Exception as e:
            print(f"\nERROR: Could not create database: {e}")
            print("  Ensure PostgreSQL is running and DB_USER has CREATEDB privileges.")
            return False
        if not database_loader.test_connection():
            print("  Connection still failing after create attempt.")
            return False

    # Step 2: Create tables
    print("[2/3] Creating tables...")
    try:
        database_loader.create_tables()
        print("  Tables created: jobs, skills, job_skills")
    except Exception as e:
        print(f"\nERROR creating tables: {e}")
        return False

    # Step 3: Load seed data
    print("[3/3] Loading seed data...")
    try:
        from src.skill_extractor import SKILL_DICTIONARY, SKILL_CATEGORIES
        import pandas as pd
        from src import database_loader as dl

        rows = [{
            "skill_id": skill,
            "skill_name": skill,
            "skill_category": SKILL_CATEGORIES.get(skill, "Other"),
        } for skill in SKILL_DICTIONARY]

        skills_df = pd.DataFrame(rows)
        engine = dl.get_engine()
        skills_df.to_sql("skills", engine, if_exists="replace", index=False, method="multi")
        print(f"  Loaded {len(skills_df)} skills into skill dictionary")
    except Exception as e:
        print(f"\nWARNING: Could not load seed data: {e}")

    print("\n" + "=" * 60)
    print("DATABASE SETUP COMPLETE")
    print("=" * 60)
    return True


def create_database() -> None:
    """Create the jobpulse_db database via the postgres server."""
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname="postgres",
        user=DB_USER,
        password=DB_PASSWORD,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    # Check if database exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    exists = cur.fetchone()
    if not exists:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
        logger.info("Created database %s", DB_NAME)
    else:
        logger.info("Database %s already exists", DB_NAME)
    cur.close()
    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Setup JobPulse AI database")
    parser.add_argument("--no-create", action="store_true", help="Do not auto-create the database")
    args = parser.parse_args()
    setup_database(auto_create=not args.no_create)