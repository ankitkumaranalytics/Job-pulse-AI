"""
Configuration module for JobPulse AI.
Loads settings from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (if exists)
load_dotenv()

# Base project root (two levels up from this file: src/config.py -> project root)
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Database Configuration (PostgreSQL)
# ---------------------------------------------------------------------------
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_NAME: str = os.getenv("DB_NAME", "jobpulse_db")
DB_USER: str = os.getenv("DB_USER", "postgres")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "your_password")

DATABASE_URL: str = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

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
