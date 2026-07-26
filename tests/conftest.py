"""Pytest configuration for importing root-level project modules."""

from pathlib import Path
import sys


# Add the repository root so tests can import the project modules.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
