"""Shared test fixtures and configuration."""

import sys
import pytest
from pathlib import Path

# Ensure src is importable from tests
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
