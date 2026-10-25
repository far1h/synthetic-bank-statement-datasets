"""Output location for generate.py; set with the OUT_DIR environment variable."""

import os
from pathlib import Path

DATA = Path(os.environ.get("OUT_DIR", "out"))
DATA.mkdir(parents=True, exist_ok=True)
