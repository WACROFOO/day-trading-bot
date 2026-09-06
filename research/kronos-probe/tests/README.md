# tests/

20 tests, every one guarding an assumption that fails **silently**.

The load-bearing one: sample paths come from repeating an anchor N times in
the batch dimension with `sample_count=1`. That only works if sampling is
independent per batch row — if the copies came back identical, every
probability would be 0 or 1 and nothing else would complain.

    python3 -m pytest research/kronos-probe/tests -q -m "not slow"

The `slow` marker loads real model weights.
