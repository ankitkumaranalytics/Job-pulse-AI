"""
JobPulse AI - Main entry point.

Provides a user-friendly CLI menu:
1. Run Data Pipeline
2. Generate Sample Dataset
3. Setup Database
4. Launch Dashboard
5. Run Tests
6. Exit
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PYTHON = sys.executable


def run_command(cmd: list[str], cwd: str = None) -> int:
    """Run a subprocess command safely and return its exit code."""
    print(f"\n> {' '.join(cmd)}\n")
    try:
        result = subprocess.run(cmd, cwd=cwd or str(ROOT))
        return result.returncode
    except FileNotFoundError as e:
        print(f"ERROR: command not found - {e}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def print_menu() -> None:
    """Print the main menu."""
    print()
    print("=" * 60)
    print("  JOBPULSE AI - Job Market & Skills Intelligence Platform")
    print("=" * 60)
    print("  1. Run Data Pipeline")
    print("  2. Generate Sample Dataset")
    print("  3. Setup Database")
    print("  4. Launch Dashboard")
    print("  5. Run Tests")
    print("  6. Exit")
    print("=" * 60)


def main() -> None:
    """Main CLI loop."""
    while True:
        print_menu()
        choice = input("\nSelect an option [1-6]: ").strip()

        if choice == "1":
            run_command([PYTHON, str(ROOT / "scripts" / "run_pipeline.py")])

        elif choice == "2":
            try:
                n = int(input("Number of records to generate [default 10000]: ").strip() or "10000")
            except ValueError:
                n = 10000
            run_command([
                PYTHON, str(ROOT / "scripts" / "generate_sample_data.py"),
                "--records", str(n)
            ])

        elif choice == "3":
            run_command([PYTHON, str(ROOT / "scripts" / "setup_database.py")])

        elif choice == "4":
            print("\nLaunching Streamlit dashboard...")
            print("Press Ctrl+C to stop the dashboard.\n")
            run_command([
                "streamlit", "run", str(ROOT / "dashboard" / "app.py")
            ])

        elif choice == "5":
            run_command(["pytest", str(ROOT / "tests"), "-v"])

        elif choice == "6":
            print("\nThank you for using JobPulse AI. Goodbye!")
            break

        else:
            print("\nInvalid option. Please choose 1-6.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)