"""Vercel entry point: exposes the site's Flask server (Dash runs on top of it) as `app`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # project root, where app.py lives

from app import server as app  # noqa: E402
