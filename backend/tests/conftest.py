"""Pytest configuration — ensures the backend package is importable."""

import sys
from pathlib import Path

# Make `app.*` importable when tests run from the backend/ directory.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
