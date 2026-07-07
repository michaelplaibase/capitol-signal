"""Pytest configuration for the Capitol Signal test suite.

Insert the repo root on sys.path so "from core..." style imports resolve when
tests run under pytest regardless of the current working directory. Test files
also perform the same insertion so they remain runnable as plain scripts.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
