"""Suite-wide: A13 selective mode off unless a test asks for it.

The runner tests were written with small, tight fixture plans ($2-$4 prices,
cent stops) to exercise order plumbing, not selection; A13 would refuse them
all. `tests/test_selective.py` turns it on and tests it directly.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture(autouse=True)
def _selective_off(request, monkeypatch):
    if "selective" in request.keywords:
        return
    from execution import runner
    monkeypatch.setattr(runner, "SELECTIVE", False)


def pytest_configure(config):
    config.addinivalue_line("markers", "selective: run with A13 selective mode on")
