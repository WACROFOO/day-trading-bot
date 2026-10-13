# desk-2026-10-13 — older candles, levels with volume density, the TradingView look, before and after

The write-up is `../desk-2026-10-13.md`. Every image here is **synthetic**: this container has
no IBKR, so the desk ran on the test suite's fake TWS (`tests/fake_ibkr.py`) with four made-up
sessions of one made-up name, `SYNTH` — two quiet days around $2.10–2.30, a spike to $3.40 that
faded, and a gap to $4.40 — drawn by the real server and the real page
(`python3 scripts/chart_shots.py`). The page carries a dashed "SYNTHETIC" label. Nothing in
these pictures is a market fact.

| file | what |
|---|---|
| `before_desk_SYNTHETIC.png`, `before_chart-1m_SYNTHETIC.png` | at `492d29e`, the same data: the 1-minute starts at today's 04:00 with empty canvas to its left; MACD squeezed under the volume, read off the price axis; a grid next to invisible |
| `after_desk_SYNTHETIC.png` | the whole desk, 1920 × 952: the 1-minute holds the afternoon before and today, the date on the axis, MACD in its own pane; the 5-minute, on its newest bar, carries the volume profile, the S/R fan and its own trend line |
| `after_chart-1m_SYNTHETIC.png` | the 1-minute: `ross-fp-v4.pine`'s S/R fan — R1 R2 above, S1 S2 below, each with its swings and `vol N×` — PD HIGH / PD CLOSE / PD LOW, the whole and half dollars, HOD and PM HIGH, each session's VWAP, today's uptrend line |
| `after_chart-1m_breakout_SYNTHETIC.png` | three live ten-second bars pushed through the downtrend line from the 09:35 high: the label flips to `downtrend BROKEN ▲` and the line turns dashed; the old 4.41 resistance now reads as support (the Pine's polarity) |
| `after_chart-1m_sessions_SYNTHETIC.png` | the 1-minute zoomed out over the four loaded sessions — dragged back from today one session at a time |
| `after_chart-1m_values_SYNTHETIC.png` | ƒ → Values ticked: TradingView's legend (symbol, interval, O H L C, change, volume, VWAP and the 9 EMA) and MACD's values in its pane, read at the crosshair, which both panes share |
| `after_chart-5m_SYNTHETIC.png` | the 5-minute: the volume profile of the bars in view — 24 rows, up blue, down amber, the value area brighter, the point of control in red |
