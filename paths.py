"""Shared path helpers.

Distinguishes two different "base directories":
- BASE_DIR (in documents.py, via __file__) for bundled read-only resources
  (LaTeX templates, fonts) -- correct even inside a PyInstaller onefile
  bundle, since __file__ resolves into the temp extraction dir where those
  bundled data files actually live.
- app_dir() (via sys.executable when frozen) for user-writable runtime
  files (customers.db, output/) that must live next to the real .exe, not
  vanish inside the temp extraction dir when the app closes.
"""
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent
