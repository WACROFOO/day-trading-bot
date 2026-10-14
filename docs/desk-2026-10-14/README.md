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

**Round four (§12), the scanner cards** — on the replay fixture's ten made-up names
(`fixtures/market_replay/workstation_open_2026-09-01.jsonl`, made by `scripts/make_replay_fixture.py`), the
static page the dashboard tests use (`scripts/build_dashboard_artifact.py`); "before" is the cards as of
`b367b70`. Also synthetic: nothing here is a market fact.

| file | what |
|---|---|
| `before_scan-pillars_0800_fixture_SYNTHETIC.png` | 08:00: "10 names on the desk · blocked by RVOL on 10" over an empty Top gainers card |
| `after_scan-pillars_0800_fixture_SYNTHETIC.png` | 08:00 now: the ten names up on the day by change, P G R F N on each row, R red on every one |
| `before_scan-pillars_1005_fixture_SYNTHETIC.png` | 10:05: four rows, "4/5" pills, a "?" button under each float |
| `after_scan-pillars_1005_fixture_SYNTHETIC.png`, `after_scan-pillars_open_fixture_SYNTHETIC.png` | 10:05 now, one line a row; the first row's ▸ open: the five checks, the name's facts |
| `before_scan-running_fixture_SYNTHETIC.png`, `before_scan-hod_fixture_SYNTHETIC.png` | two lines an alert: the row with PM/RTH, ×N, "new high", then "now … vs high … high … ago" |
| `after_scan-running_fixture_SYNTHETIC.png`, `after_scan-hod_fixture_SYNTHETIC.png` | one line an alert: ▸, time, change, name, ×N, price, label, NOW |
| `after_scan-running_open_fixture_SYNTHETIC.png` | an alert's ▸ open: the name now, the session, its four alerts, the label, what it fired on |
