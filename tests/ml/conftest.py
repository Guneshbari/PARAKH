"""Pytest configuration and fixtures for PARAKH ML test suite."""
import os
import sys
from pathlib import Path

# Add project root directory to sys.path so 'src' can be imported anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
