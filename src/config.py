"""
Configuration module for JobPulse AI.

Configuration priority (highest first):
1. Streamlit Secrets (st.secrets) - for Streamlit Community Cloud
2. Environment variables
3. .env file (local development only - optional, never required)

The application must NEVER require a database or a .env file to run:
the dashboard falls back to processed CSV data when PostgreSQL is
unavailable or unconfigured.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (no-op when the file is absent)
load_dotenv()

# Base project root (two levels up from this file: src/config.py -> project root)
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Database Configuration (PostgreSQL) - entirely OPTIONAL
# ---------------------------------------------------------------------------
# Precedence: Streamlit secrets -> environment variables -> .env -> defaults.
# An empty DB_PASSWORD means the database is treated as NOT configured and
# all consumers fall back to processed CSV data (no connection is attempted).


def _get_setting(key: str, default: str = "") -> str:
    """Read a setting from Streamlit secrets, then env vars, then default."""
    # 1. Streamlit secrets (safe import: src is also used outside Streamlit)
    try:
        import streamlit as st  # noqa: PLC0415 - deferred import

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:  # streamlit not installed / not running / no secrets file
        pass
    # 2. Environment variable
    return os.getenv(key, default)


def get_db_config() -> dict[str, str] | None:
    """
    Return database connection settings, or ``None`` when unconfigured.

    Returns None if DB_ENABLED is explicitly 'false' or if no password is
    provided (placeholder-free default keeps local dev from attempting
    doomed connections). Never logs or exposes secrets.
    """
    enabled = _get_setting("DB_ENABLED", "").strip().lower()
    if enabled == "false":
        return None

    password = _get_setting("DB_PASSWORD", "")
    if not password:
        # No credentials -> database intentionally unconfigured
        return None

    return {
        "host": _get_setting("DB_HOST", "localhost"),
        "port": _get_setting("DB_PORT", "5432"),
        "name": _get_setting("DB_NAME", "jobpulse_db"),
        "user": _get_setting("DB_USER", "postgres"),
        "password": password,
    }


def build_database_url(cfg: dict[str, str]) -> str:
    """Build a SQLAlchemy URL from a db config dict (never log the result)."""
    return (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['name']}"
    )


# Backwards-compatible module-level access (pipeline scripts).
# NOTE: callers must check `is_db_configured()` before using DATABASE_URL.
_DB_CFG = get_db_config()
DB_HOST: str = _DB_CFG["host"] if _DB_CFG else "localhost"
DB_PORT: int = int(_DB_CFG["port"]) if _DB_CFG else 5432
DB_NAME: str = _DB_CFG["name"] if _DB_CFG else "jobpulse_db"
DB_USER: str = _DB_CFG["user"] if _DB_CFG else "postgres"
DB_PASSWORD: str = _DB_CFG["password"] if _DB_CFG else ""
DATABASE_URL: str = build_database_url(_DB_CFG) if _DB_CFG else ""


def is_db_configured() -> bool:
    """True when database credentials are available (secrets/env/.env)."""
    return bool(DATABASE_URL)


# ---------------------------------------------------------------------------
# Data Paths
# ---------------------------------------------------------------------------
DATA_PATH: str = os.getenv("DATA_PATH", str(BASE_DIR / "data" / "raw" / "jobs.csv"))
DATA_OUTPUT_DIR: str = os.getenv("DATA_OUTPUT_DIR", str(BASE_DIR / "data" / "processed"))
RAW_DATA_DIR: str = str(BASE_DIR / "data" / "raw")
CLEANED_DATA_DIR: str = str(BASE_DIR / "data" / "cleaned")

# ---------------------------------------------------------------------------
# Processing Settings
# ---------------------------------------------------------------------------
RANDOM_SEED: int = 42
MAX_RECORDS_DEFAULT: int = 10000
DUPLICATE_THRESHOLD: float = 0.85  # For near-duplicate detection

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("jobpulse")

# ---------------------------------------------------------------------------
# Job role categories (used across multiple modules)
# ---------------------------------------------------------------------------
JOB_ROLE_CATEGORIES: list[str] = [
    "Data Analyst",
    "Business Analyst",
    "Data Scientist",
    "Data Engineer",
    "Machine Learning Engineer",
    "BI Analyst",
    "Analytics Engineer",
    "Other",
]

# ---------------------------------------------------------------------------
# Experience Categories
# ---------------------------------------------------------------------------
EXPERIENCE_CATEGORIES: list[str] = [
    "Fresher",
    "Entry Level",
    "Mid Level",
    "Senior Level",
]
