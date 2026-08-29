"""
Pytest configuration - ensures project root is on the path.
"""
import sys
from pathlib import Path

# Add project root so `from src...` and `from models...` imports work
# (conftest.py lives in tests/, so the root is two levels up)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))