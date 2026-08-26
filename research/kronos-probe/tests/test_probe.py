"""Tests for the assumptions the probe would fail silently on.

Every one of these guards something that produces plausible numbers when
broken. The expensive failure mode is not a crash — it is a well-formed
result that means nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/user/shiyu-coder/kronos")

from run_probe import _auc                                    # noqa: E402
from src import bars as bars_mod                              # noqa: E402
from src.forecast import barrier_probabilities, stamp, to_features  # noqa: E402
from src.truth import barrier_outcome                         # noqa: E402


# ---------------------------------------------------------------- fixtures
def _bar(ts, o, h, l, c, v=1000):
    return [ts, o, h, l, c, v]


def _fake_session(monkeypatch, sym, day, rows):
    monkeypatch.setattr(bars_mod, "session_bars",
                        lambda s, d: rows if (s, d) == (sym, day) else [])


# ---------------------------------------------------- session containment
def test_context_window_never_crosses_a_session(monkeypatch):
    """The whole point of the drop rule: 150 bars back from the open would
    otherwise reach into yesterday, and the overnight gap is the event."""
    day_rows = [_bar(1000 + 60 * i, 5, 5, 5, 5) for i in range(10)]
    _fake_session(monkeypatch, "AAA", "2024-01-02", day_rows)
    assert bars_mod.context_window("AAA", "2024-01-02", 1000 + 60 * 9, 5) is not None
    # only 10 bars exist in the session; asking for 20 must refuse, not borrow
    assert bars_mod.context_window("AAA", "2024-01-02", 1000 + 60 * 9, 20) is None


def test_context_window_excludes_bars_after_the_anchor(monkeypatch):
    """A context window that includes the anchor's future is look-ahead."""
    rows = [_bar(1000 + 60 * i, 5, 5 + i, 5, 5) for i in range(10)]
    _fake_session(monkeypatch, "AAA", "2024-01-02", rows)
    win = bars_mod.context_window("AAA", "2024-01-02", 1000 + 60 * 4, 3)
    assert [r[0] for r in win] == [1000 + 60 * 2, 1000 + 60 * 3, 1000 + 60 * 4]
    assert max(r[0] for r in win) <= 1000 + 60 * 4


def test_forward_bars_start_strictly_after_the_anchor(monkeypatch):
    rows = [_bar(1000 + 60 * i, 5, 5, 5, 5) for i in range(10)]
    _fake_session(monkeypatch, "AAA", "2024-01-02", rows)
    fwd = bars_mod.forward_bars("AAA", "2024-01-02", 1000 + 60 * 4, 3)
    assert [r[0] for r in fwd] == [1000 + 60 * 5, 1000 + 60 * 6, 1000 + 60 * 7]


# -------------------------------------------------------- barrier scoring
def test_truth_ambiguous_bar_scores_as_loss(monkeypatch):
    """One bar spanning both barriers: with OHLC alone there is no evidence
    for the favourable ordering, so it must not be credited as a win."""
    rows = [_bar(1060, 10, 12.0, 8.0, 10)]          # spans +2 and -2
    _fake_session(monkeypatch, "AAA", "2024-01-02", rows)
    out = barrier_outcome("AAA", "2024-01-02", 1000, entry=10.0, risk=1.0)
    assert out["outcome"] == "loss"


def test_truth_first_touch_ordering(monkeypatch):
    """A later winning bar must not overturn an earlier losing one."""
    rows = [_bar(1060, 10, 10.5, 8.5, 9),           # touches -1 first
            _bar(1120, 9, 12.0, 9.0, 11)]           # would have hit +1 later
    _fake_session(monkeypatch, "AAA", "2024-01-02", rows)
    out = barrier_outcome("AAA", "2024-01-02", 1000, entry=10.0, risk=1.0)
    assert out["outcome"] == "loss" and out["t_loss"] == 0


def test_truth_neither_is_not_a_loss(monkeypatch):
    """An untouched horizon is a real third outcome. Folding it into the
    losers would understate the win rate of every population equally and
    quietly change what the comparison means."""
    rows = [_bar(1060 + 60 * i, 10, 10.2, 9.8, 10) for i in range(5)]
    _fake_session(monkeypatch, "AAA", "2024-01-02", rows)
    out = barrier_outcome("AAA", "2024-01-02", 1000, entry=10.0, risk=1.0)
    assert out["outcome"] == "neither"


def test_truth_missing_tape_is_flagged_not_guessed(monkeypatch):
    _fake_session(monkeypatch, "AAA", "2024-01-02", [])
    out = barrier_outcome("AAA", "2024-01-02", 1000, entry=10.0, risk=1.0)
    assert out["outcome"] == "no_data"


# ----------------------------------------------- path reduction semantics
def _paths(seq):
    """seq: list of (high, low) per bar -> (1, 1, T, 6) path array."""
    arr = np.zeros((1, 1, len(seq), 6))
    for i, (h, l) in enumerate(seq):
        arr[0, 0, i] = (0, h, l, (h + l) / 2, 0, 0)
    return arr


def test_reduction_matches_the_truth_rule_on_ambiguity():
    """The model's paths and the real tape must be graded identically, or
    the comparison is between two different questions."""
    amb = _paths([(12.0, 8.0)])
    s = barrier_probabilities(amb, np.array([10.0]), np.array([1.0]))
    assert s["p_win"][0] == 0.0


def test_reduction_first_touch_ordering():
    s = barrier_probabilities(_paths([(10.5, 8.5), (12.0, 9.0)]),
                              np.array([10.0]), np.array([1.0]))
    assert s["p_win"][0] == 0.0
    s2 = barrier_probabilities(_paths([(11.5, 9.5), (10.0, 8.0)]),
                               np.array([10.0]), np.array([1.0]))
    assert s2["p_win"][0] == 1.0


def test_reduction_untouched_horizon_is_not_a_win():
    s = barrier_probabilities(_paths([(10.2, 9.8), (10.1, 9.9)]),
                              np.array([10.0]), np.array([1.0]))
    assert s["p_win"][0] == 0.0
    assert s["p_touch_up"][0] == 0.0


def test_reduction_averages_over_paths_not_prices():
    """p_win must be the fraction of paths that won — NOT the outcome of an
    averaged path. Averaging first is the bug this whole module exists to
    avoid, and it would show up as a probability that is only ever 0 or 1."""
    arr = np.zeros((1, 4, 1, 6))
    for k, (h, l) in enumerate([(11.5, 9.9), (11.5, 9.9), (10.1, 8.5), (10.1, 9.9)]):
        arr[0, k, 0] = (0, h, l, 10, 0, 0)
    s = barrier_probabilities(arr, np.array([10.0]), np.array([1.0]))
    assert s["p_win"][0] == pytest.approx(0.5)


# ------------------------------------------------------------ timestamps
def test_stamp_is_exchange_local_not_utc():
    """Kronos indexes real calendar fields; UTC would put the US open at
    13:30 and shift every learned session shape by the offset."""
    # 2024-01-02 14:30 UTC == 09:30 America/New_York
    minute, hour, weekday, day, month = stamp(1704205800)
    assert (hour, minute) == (9, 30)
    assert (day, month) == (2, 1)
    assert weekday == 1                                   # Tuesday


# -------------------------------------------------------------- features
def test_amount_matches_the_predictor_convention():
    rows = [_bar(1000, 2.0, 4.0, 1.0, 3.0, 100)]
    f = to_features(rows)
    assert f[0, 5] == pytest.approx(100 * (2.0 + 4.0 + 1.0 + 3.0) / 4.0)


# ------------------------------------------------------------------- auc
@pytest.mark.parametrize("score,label,want", [
    ([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1], 1.0),
    ([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1], 0.0),
    ([0.5, 0.5, 0.5, 0.5], [0, 0, 1, 1], 0.5),
])
def test_auc_known_cases(score, label, want):
    assert _auc(np.array(score), np.array(label)) == pytest.approx(want)


def test_auc_credits_ties_at_half():
    """With N sampled paths p_win is quantised to multiples of 1/N, so ties
    are common. Breaking them in the winners' favour would inflate the
    headline number for free.

    Four (positive, negative) pairs, worked by hand:
        (0.5, 0.5) tie  -> 0.5
        (0.5, 0.1) win  -> 1
        (0.9, 0.5) win  -> 1
        (0.9, 0.1) win  -> 1     = 3.5 / 4 = 0.875
    Breaking the tie in the winner's favour would give 1.0 instead.
    """
    got = _auc(np.array([0.5, 0.5, 0.1, 0.9]), np.array([1, 0, 0, 1]))
    assert got == pytest.approx(0.875)
    # and the tie must actually cost something
    assert got < 1.0


# ------------------------------------------- the core design assumption
@pytest.mark.slow
def test_batch_replication_yields_distinct_paths():
    """THE assumption this module rests on.

    Sample paths are obtained by repeating one anchor N times in the batch
    dimension and calling Kronos with sample_count=1, so that its
    `np.mean(preds, axis=1)` becomes a no-op instead of averaging the paths
    away. That only works if sampling is independent per batch row.

    If it were not — if the N copies came back identical — every p_win would
    be exactly 0 or 1 and the whole probe would produce confident, meaningless
    numbers. Nothing else in the pipeline would complain.
    """
    from model import Kronos, KronosTokenizer
    from src.forecast import Forecaster

    rng = np.random.default_rng(0)
    ctx = np.cumsum(rng.normal(0, 0.01, size=(1, 64, 6)), axis=1) + 10.0
    ctx[:, :, 4:] = np.abs(ctx[:, :, 4:]) * 1000          # volume, amount > 0
    ts = [[1704205800 + 60 * i for i in range(64)]]

    fc = Forecaster(KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base"),
                    Kronos.from_pretrained("NeoQuasar/Kronos-small"), device="cpu")
    paths = fc.paths(ctx, ts, [ts[0][-1]], pred_len=3, n_paths=6)

    assert paths.shape == (1, 6, 3, 6)
    closes = paths[0, :, :, 3]
    assert len(np.unique(closes.round(6))) > 1, (
        "all sampled paths identical — the sample axis is a copy, not a sample")
