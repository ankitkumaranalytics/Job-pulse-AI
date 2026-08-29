"""
Run the complete JobPulse AI data pipeline.

Executes:
[1/9] Load raw data
[2/9] Validate data
[3/9] Clean data
[4/9] Extract skills
[5/9] Feature engineering
[6/9] Save processed data (+ Power BI exports)
[7/9] Load PostgreSQL database
[8/9] Generate analytics summaries
[9/9] Generate business insights report
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import logger, DATA_OUTPUT_DIR, CLEANED_DATA_DIR
from src.data_loader import load_raw_data, detect_and_rename_columns
from src.data_validator import validate_data
from src.data_cleaning import clean_data, save_cleaned_data
from src.skill_extractor import extract_skills, save_skill_dictionary
from src.feature_engineering import engineer_features, save_processed_data
from src import database_loader

STEPS = [
    "Loading raw data",
    "Validating data",
    "Cleaning data",
    "Extracting skills",
    "Feature engineering",
    "Saving processed data",
    "Loading database",
    "Generating analytics summaries",
    "Generating business insights report",
]


def step_header(step_num, total, name):
    print(f"\n[{step_num}/{total}] {name}...")


def run_pipeline(data_path=None, load_to_db=True, skip_db=False):
    """
    Run the full ETL pipeline.

    Parameters
    ----------
    data_path : str | None
        Path to raw CSV data.
    load_to_db : bool
        Whether to attempt loading into PostgreSQL (default True).
    skip_db : bool
        Force-skip the database step.

    Returns
    -------
    dict
        Summary of pipeline execution results.
    """
    total = len(STEPS)
    results = {}

    # [1/9] Load raw data
    step_header(1, total, STEPS[0])
    try:
        raw_df = load_raw_data(data_path)
        raw_df = detect_and_rename_columns(raw_df)
        results["raw_rows"] = len(raw_df)
        print(f"  Loaded {len(raw_df)} rows, {len(raw_df.columns)} columns")
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("  Tip: Run 'python scripts/generate_sample_data.py' first.")
        sys.exit(1)
    except Exception:
        print("\nERROR loading data:")
        traceback.print_exc()
        sys.exit(1)

    # [2/9] Validate data
    step_header(2, total, STEPS[1])
    try:
        report = validate_data(raw_df, report_dir=CLEANED_DATA_DIR)
        results["duplicates"] = report.duplicate_rows
        results["warnings"] = len(report.warnings)
        print(f"  Validation: {report.total_rows} rows, {report.duplicate_rows} dupes, "
              f"{len(report.warnings)} warnings")
    except Exception as e:
        print(f"WARNING: validation step failed: {e}")

    # [3/9] Clean data
    step_header(3, total, STEPS[2])
    try:
        cleaned_df = clean_data(raw_df)
        results["cleaned_rows"] = len(cleaned_df)
        save_cleaned_data(cleaned_df, Path(CLEANED_DATA_DIR) / "jobs_cleaned.csv")
        print(f"  Cleaned: {len(cleaned_df)} rows")
    except Exception:
        print("\nERROR in cleaning:")
        traceback.print_exc()
        sys.exit(1)

    # [4/9] Extract skills
    step_header(4, total, STEPS[3])
    try:
        cleaned_df = extract_skills(cleaned_df)
        save_skill_dictionary(Path(DATA_OUTPUT_DIR) / "skill_dictionary.csv")
        total_skills = sum(len(s) for s in cleaned_df["extracted_skills"])
        print(f"  Skills extracted: {total_skills} across {len(cleaned_df)} jobs")
    except Exception:
        print("\nERROR extracting skills:")
        traceback.print_exc()
        sys.exit(1)

    # [5/9] Feature engineering
    step_header(5, total, STEPS[4])
    try:
        processed_df = engineer_features(cleaned_df)
        results["processed_rows"] = len(processed_df)
        print(f"  Feature engineering complete: {len(processed_df)} rows")
    except Exception:
        print("\nERROR in feature engineering:")
        traceback.print_exc()
        sys.exit(1)
# [6/9] Save processed data + Power BI exports
    step_header(6, total, STEPS[5])
    try:
        path = save_processed_data(processed_df, Path(DATA_OUTPUT_DIR) / "jobs_processed.csv")
        results["processed_path"] = path
        print(f"  Processed data saved: {path}")
        try:
            from scripts.export_powerbi import export_powerbi_files
            export_powerbi_files(processed_df, output_dir=DATA_OUTPUT_DIR)
            print("  Power BI CSV exports generated")
        except ImportError:
            _export_summaries_inline(processed_df)
        except Exception as e:
            print(f"  WARNING: Power BI export failed: {e}")
    except Exception:
        print("\nERROR saving processed data:")
        traceback.print_exc()
        sys.exit(1)

    # [7/9] Load into PostgreSQL (optional)
    step_header(7, total, STEPS[6])
    if skip_db:
        print("  Database step skipped (--skip-db)")
    elif not load_to_db:
        print("  Database step skipped (load_to_db=False)")
    else:
        try:
            db_summary = database_loader.load_all_data(processed_df)
            results["db"] = db_summary
            print(f"  Loaded {db_summary['jobs_loaded']} jobs and "
                  f"{db_summary['skills_loaded']} skills into PostgreSQL")
        except Exception as e:
            print(f"\n  WARNING: Database step failed (continuing): {e}")
            print("  Ensure PostgreSQL is running and .env credentials are correct.")
            results["db_error"] = str(e)

    # [8/9] Analytics summaries
    step_header(8, total, STEPS[7])
    try:
        from scripts.export_powerbi import export_powerbi_files
        export_powerbi_files(processed_df, output_dir=DATA_OUTPUT_DIR)
        print("  Analytics summaries written to data/processed/")
    except ImportError:
        _export_summaries_inline(processed_df)
    except Exception as e:
        print(f"  WARNING: analytics summary step failed: {e}")

    # [9/9] Business insights report
    step_header(9, total, STEPS[8])
    try:
        # Load scripts/generate_report.py directly from its file path,
        # since the scripts folder is not an installed package.
        import importlib.util
        report_script = ROOT / "scripts" / "generate_report.py"
        spec = importlib.util.spec_from_file_location("generate_report", report_script)
        report_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(report_module)
        report_path = report_module.generate_business_insights(processed_df)
        results["report_path"] = report_path
        print(f"  Business insights report: {report_path}")
    except Exception as e:
        print(f"  WARNING: report generation failed: {e}")

    # -----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Raw rows:      {results.get('raw_rows', '?')}")
    print(f"  Cleaned rows:  {results.get('cleaned_rows', '?')}")
    print(f"  Duplicates:    {results.get('duplicates', '?')}")
    print(f"  Processed:     {results.get('processed_rows', '?')}")
    if "db" in results:
        print(f"  DB jobs:       {results['db']['jobs_loaded']}")
        print(f"  DB skills:     {results['db']['skills_loaded']}")
    elif "db_error" in results:
        print(f"  DB load:       FAILED ({results['db_error'][:80]})")

    return results


def _export_summaries_inline(df):
    """Inline fallback to export analyst summary CSVs."""
    from pathlib import Path
    out_dir = Path(DATA_OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    from src import analytics
    analytics.get_top_skills(df, n=50).to_csv(out_dir / "skills_summary.csv", index=False)
    analytics.get_top_companies(df, n=50).to_csv(out_dir / "company_summary.csv", index=False)
    analytics.get_top_locations(df, n=50).to_csv(out_dir / "location_summary.csv", index=False)
    analytics.get_salary_by_role(df).to_csv(out_dir / "salary_summary.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the JobPulse AI data pipeline")
    parser.add_argument("--data", type=str, default=None, help="Path to raw CSV data")
    parser.add_argument("--skip-db", action="store_true", help="Skip PostgreSQL loading")
    parser.add_argument("--no-db", action="store_true", help="Skip database step")
    args = parser.parse_args()

    run_pipeline(data_path=args.data, load_to_db=not args.no_db, skip_db=args.skip_db)