"""Shared path + import resolution for this package.

Every script resolves its data directory and its sibling modules through here,
so the package can be moved or run from any working directory.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data')

for sub in ('engine', 'pipeline', 'diagnostics'):
    p = os.path.join(ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.makedirs(DATA, exist_ok=True)
