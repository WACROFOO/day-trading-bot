# desk-2026-10-14 — trend lines through two swings, the overlay switches, before and after

The write-up is `../desk-2026-10-14.md`. Every image here is **synthetic**: the desk ran on the
test suite's fake TWS (`tests/fake_ibkr.py`) with the made-up name `SYNTH` of
`scripts/chart_shots.py`, drawn by the real server and the real page; "before" is commit
`1a52847` drawing the same data. The page carries a dashed "SYNTHETIC" label. Nothing in these
pictures is a market fact.

| file | what |
|---|---|
| `before_chart-1m_breakout_SYNTHETIC.png` | at `1a52847`: the tangent up-line from an anchor off the left edge, under every candle on screen; the down-line from the high nearly flat |
| `after_chart-1m_breakout_SYNTHETIC.png` | now, same data: the up-line through the 09:11 and 09:55 lows, the down-line from the high of day through the 10:07 lower high, `downtrend BREAKING ▲` under three live ten-second bars pushed through it |
| `before_chart-5m_SYNTHETIC.png` | at `1a52847`: the 5-minute tangent up-line from the session's first bar |
| `after_chart-5m_SYNTHETIC.png` | now: the morning's down-line dashed to the candle that closed through it, `downtrend BROKEN ▲` |
| `after_desk_SYNTHETIC.png` | the whole desk, 1920 × 952, at the desk's own minute (10:16): the S/R · trend · profile switches on each chart card's header (lit = on), the pillar tiles, the trimmed card, the live alert rows |
| `after_scan-running_SYNTHETIC.png`, `after_scan-hod_SYNTHETIC.png` | the two alert cards: each row's alert, and under it the name now — "now 4.39 · −2.2% vs high 4.49 · high 42m ago"; the 09:33 High of Day row dimmed, its newest alert 43 minutes old |
