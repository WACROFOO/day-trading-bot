# The trading day — runbook

One command runs the day. This page is what happens around it.

## Once, before the first session

In IBKR Client Portal › Settings › Paper Trading Account, enable sharing
of **real-time market data** with the paper account. Without it IBKR judges
paper fills against delayed prices while decisions are made on live ones;
the morning command measures this and blocks real orders until it reads
`realtime`.

## Is the market open?

The command checks the NYSE calendar (`src/momentum_platform/holidays.py`)
and does not run the bot on a weekend or holiday, naming which. 7 September
2026 was Labor Day; the chain ran all morning on a stale feed before this
check existed. Since 2026-10-08 it brings up the desk alone on those days
(see "Any hour — the platform" below).

## One login, one tape (the design since 8 September)

On 7 September the paper session was refused market data with IBKR error
10197, *"No market data during competing live session"*: a live TWS login
holds the subscriptions and the paper Gateway cannot share them while TWS
is logged in. The alignment probe reports this as `competing`.

The fix is a single login. The **desk reads and the executor writes on the
same paper session** (port 4002, `IBKR_PORT=4002`). The desk connection
stays read-only; only the executor's connection may write. Decisions and
orders then share one tape by construction, and the alignment probe runs in
single-login mode.

## Before 06:55 ET (12:55 France)

1. Once, in Client Portal › Settings › Account Settings › Paper Trading
   Account: share real-time market data subscriptions with the paper
   account. Log the Gateway out and back in afterwards. (Done 7 September.)
2. **TWS logged out.** Log **IB Gateway** in on the **paper** account,
   port 4002. That is the only login; it needs 2FA, which is why it is not
   automated.
3. First trading day only, or after any rehearsal: move the rehearsal
   ledger aside so the exercise starts from a clean file. The rehearsals of
   7 September wrote decisions and orders into it that are not sessions.
   ```bash
   cd ~/day-trading-bot && git pull origin claude/playbook-pullback-explanation-tg5c33
   mv data/journal.sqlite data/journal-rehearsals-2026-09-07.sqlite
   ```
4. Prove the paper session has the tape (from 07:00 ET, when bars exist):
   ```bash
   IBKR_PORT=4002 python3 scripts/ibkr_preflight.py
   ```
   Wants `market data type 1` and five-second bars arriving. If it shows
   type 3 (delayed) or no bars with TWS out, the sharing setting has not
   taken effect: the day still runs, but `paper_data` will not read
   `realtime` and the phase gate keeps orders off.

## 06:55–11:30 ET — one command

```bash
cd ~/day-trading-bot && bash scripts/go.sh
```

`scripts/go.sh` (owner, 2026-10-09: "update command and day start at one
command") runs `scripts/update.sh`, then `IBKR_PORT=4002 python3 scripts/day.py`
with any flags you add (`bash scripts/go.sh --symbols X,Y`). A failed update —
no network — starts the day on the code on disk, as the scheduled job does. A
day already running is never replaced: you get its link, and its desk is
restarted on the new code when the bot is not trading (it records nothing
then); during the bot's window you are given the command instead. Without the
update, the day alone is `IBKR_PORT=4002 python3 scripts/day.py`.

**To restart a day already started, on new code** (owner, 2026-10-09), run
this in a new terminal tab:

```bash
cd ~/day-trading-bot && bash scripts/update.sh && bash scripts/restart.sh
```

`scripts/restart.sh` handles three cases:

- **No day is running:** it starts one.
- **A day is running and the bot is flat:** it stops the day cleanly
  (SIGINT, as Ctrl-C), waits for the day and its desk to be gone, then
  starts the day again in this tab.
- **The bot holds a position, or placed an entry in the last 10 minutes**
  (`python3 scripts/exercise.py busy` exits 3): it does **not** stop the
  day, because a stopped runner leaves the monitored stop unwatched. It
  restarts the desk alone on the new code; run the command again once the
  bot is flat.

The day stopped this way is settled at its next start, as after a Ctrl-C.

What it does, in Ross's order (`scripts/day.py`):

| step | what | where the rule lives |
|---|---|---|
| 1 | gap scan → watchlist: STAR then WATCH, rejects named; its finviz floats are handed to the desk so Layer 0 and Layer 1 agree on float | `scripts/premarket_stars.py` → the daily float file under `data/` |
| 2 | two probes, once per day: is the paper account on the live tape (`scripts/alignment_probe.py`, single-login mode); does a pre-market stop hold (`scripts/premarket_probe.py`, at 07:00 ET). Both verdicts recorded | `exercise_state` |
| 3 | desk starts on the watchlist, journaling every rebuild until 11:31:30 ET | `JOURNAL_DB` → `src/journal/ledger.py` · `DESK_RECORD_UNTIL` |
| 4 | runner starts in the phase's mode (A = log only) | `docs/preregistration.md` §3 |
| 5 | hard stop 11:30: runner flattens (TRADE mode) and is stopped 90 s later; the desk stays up | `PARAMETERS.md` §2 · `src/execution/intent.py` |
| 6 | actuals, replay check, controls, report, sessions_done += 1 | one file per day in `research/paper-exercise/reports/` |

Leave it running. `Ctrl-C` stops both processes cleanly. Missed the
morning? Run the same command after 11:30: it does step 6, then brings up
the desk.

Browser desk: `http://127.0.0.1:8787`. The bottom-right verdict is the
server's cascade word; a killed name reads `suppressed · KILLED` on the
Entry line, never `ARMED`.

## Any hour — the platform (since 2026-10-08)

The same command brings the desk up at any hour, closed days included, and it
stays up until Ctrl-C. Only the desk: **the bot keeps its window**.

| when you run it | what happens |
|---|---|
| a trading day, 06:55–11:30 ET | the day above; at 11:30 the runner flattens and is stopped 90 s later, the day is settled, and the desk carries on |
| after 11:30 | step 6 for the day — once: a day already settled is not settled again — then the desk |
| before 06:55 | the desk now; the day starts at 06:55 in the same run (`--early` still starts the day at once) |
| weekend or NYSE holiday | the desk, the closure named, no bot |
| while a day already runs | nothing new starts — a second desk on client 27 knocks the first offline (2026-09-21). It prints the desk's link (and opens it, from a terminal) and says when that desk runs older code than the checkout, with the command below |

A desk outside the bot's day:

- **writes nothing to the exercise ledger** — no decision, bar, quote, board
  row, halt or 5-minute state (`DESK_RECORD_UNTIL=0`). The day's own desk
  writes until **11:31:30 ET**, the hard stop plus the runner's 90-s flatten:
  the moment this command used to stop it. The report, the replay check and
  settle therefore measure what they measured before, and "close" in the
  control series keeps its meaning (`src/journal/controls.py`). The day is
  settled a minute after that, on a ledger nothing writes to;
- **saves your calls and your risk at any hour**. Calls logged after the day's
  export (about 11:32 ET) are exported again for that day ten minutes after
  the newest one, and at the end of the desk-only run for any left;
- **does not keep the Mac awake** — the caffeinate hold ends with the bot's
  day. A desk that drops (sleep, the Gateway's restart) is started again once
  the Gateway answers; if it keeps failing, 1, 2, 4 … up to 15 min apart;
- **hands over to the next trading day by itself** at 06:55 ET, as the
  scheduled job would: the desk stops, up to two minutes for the network,
  one pull of the branch, then the day on that code — with the lock held
  throughout, so the scheduled 06:55 job finds it and steps aside. From the
  scheduled job the day carries on in the same process and log. **From a
  terminal the day starts in the background** in its own session, writing to
  `~/Library/Logs/day-trading-bot/day.out.log`, and the terminal command ends
  with the day's pid (`kill -INT` it to stop the day): a closed window would
  otherwise end the day mid-session, and the daily export reads the day from
  that log. Flags from your launch (`--symbols`, `--early`, `--probe-orders`)
  apply to that launch only, and `data/probe-orders.once` waits for the day
  that runs. Ctrl-C during the hand-over starts no day.

**After an update:** `bash scripts/go.sh` does it in one go — it updates, then
restarts an idle desk by itself. During the bot's window it leaves the desk
alone and names `python3 scripts/day.py --restart-desk`. It stops the running desk; the day
that started it starts it again on the new code — the runner is not touched —
and the command waits until the desk answers on the new commit. It refuses
while the desk is still coming up (the day would read that as a desk that
failed to start) and when the new code does not import; a restart that does
not come up is handled as an outage, never as the end of the day. A day
started before this existed restarts its desk the same way. With no day
running it says so: run `python3 scripts/day.py`.

## Reading the desk (since 2026-10-08)

The desk reads left to right the way a trade is made. **Find** on the left: the
scanners and the Five Pillars verdict list. **See** in the centre: the charts
under a one-line header. **Decide** on the right: the verdict card over the
Time & Sales. The quote card waits in the tray (Cards); Layout puts the desk
back to this.

Since 2026-10-09 05:30 (`docs/desk-verdict-first-2026-10-09.md`) the desk
answers in this order:

1. **The top bar says whether anything is in play.** It shows
   `NOTHING TO TRADE` when every name is NO, otherwise the best word and the
   names carrying it. A click shows the first of those names.
2. **The Five Pillars board lists the names in play.** Each row has the
   server's word, its one reason and the pillars it misses. Every NO folds
   into one line that opens to each name's killing reason.
3. **The header is one line:** name, price, change and the word with its
   reason. `HALTED` and an old print show only when true.
4. **The card leads with the answer.** First the word and what to do (skip
   it / keep it on screen / hands off until the level / read the chart and
   the tape), then the reason and the level that changes it, then the five
   pillars as value chips. On a name in play it adds the chart gates, the
   tape, the headline and the bot's line. Everything else — the catalyst
   read, filings, warnings, every lamp — sits under "Why, in full".
5. **The order area appears only where an order can exist.** A NO card has
   none.
6. **The tape follows the window you look at.** A tab out of view never
   moves it. A tape on another name says so in one line, with a "show"
   button.

Since 2026-10-09 (`docs/desk-grid-audit-2026-10-09.md`):

- **A click in the tray never replaces the decision card.** Click the card a
  tray card should replace, then the tray card — or drag it there.
- **D** switches the 5-minute pane to the daily chart and back (his minimum
  layout links the 1-minute, the 5-minute and the daily).
- The 1-minute chart draws the **pre-market high** beside the HOD ("HOD = PM
  HIGH" when they are one price). MACD is on the 1-minute only.
- The gainers list shows names **green on the day with 4 or 5 pillars**. The
  alert tiles show **one row per name with ×N** when it fired again — the
  repeat is the signal — and dim names not up 10 % at the alert. The High of
  Day tile carries the **halts** from 09:30. Maximized (E), the pillar board
  is the full table, folding red names and names with no print yet.
- **Level 2** sits beside the Time & Sales: the selected name's book from IBKR
  SmartDepth. Until the account holds a depth subscription it reads **NO SUB**
  with IBKR's own code and words, and asks again every two minutes (below,
  "Level 2").

Since 2026-10-09 07:41 (`docs/desk-recording-2026-10-09.md`):

- **The card at a glance:** the word and what to do — never "until the level"
  when there is no level — the one reason, the level, and the five pillars as
  tiles (value, threshold, the cascade's count). The ORDER on REVIEW only.
  Everything else is under "Why, in full".
- **Plan lines and the order only for a plan live now:** formed inside the
  bot's 07:00–11:20 window, inside its 3-minute fill window (A10), not stopped,
  not at 2R. Otherwise no lines, and the card says "no live plan — waiting for
  the next pullback".
- **Huge orders:** a price level within the first 3 of its side holding at
  least 10× the book's median level (never under 2,000 shares) or 25,000
  shares, appearing or gone (taken or pulled), and a print at or over the
  tape's big-print line: a banner and a sound for the selected name, at most
  one per kind every 20 s. This desk's Approximation; facts, never a gate.
- **Charts:** the 1-minute follows the selection; one crosshair across the
  intraday panes; one session VWAP on every pane; live, the forming 1-minute
  candle moves with each 10-second bar; on by default only what the verdict
  reads.
- **Running Up** also lists the discovery filters: `5%·low` (5 % off the
  5-minute low), `VOL` (3 % in 2 minutes on 2× volume), `HOD·vol`, `HALT↑` (the
  first print after a halt it ran into) — $2–20, 07:00–11:30, one alert per
  leg (`research/running-up-2026-10-09/`). Discovery only: it gates nothing.

The decision card is the server's read of the selected name
(`src/momentum_platform/decision_card.py`); the page recomputes nothing.

| line | what it says |
|---|---|
| **REVIEW / WATCH / WAIT / NO** + reason | the one reason that decides. REVIEW = a first pullback is in front of you with every gate green: read the chart. Never "buy" |
| ▸ level | the price that changes the answer: the trigger, the VWAP to reclaim, the line that puts a faded name back inside 25 % |
| setup | the first-pullback machine: the push, the pullback bars, the last plan and what became of it |
| **tape** | the Time & Sales in one line: the share of the last 60 s at the ask, prints a minute, big prints, the last print's age |
| catalyst | the grade and its reason, the headline in two lines, type · age · source, the dilution and split flags (`knowledge-base/strategies/CATALYST.md`) |
| **bot** | what the runner did with this name's latest plan (refused and why, armed, in, out) |
| lamps | every gate the bot applies, value beside threshold (⛶ / E for the full table) |
| your risk | the box above the order: your risk per trade, kept in the ledger (`desk_settings`). **Empty sizes nothing** — no fallback to the bot's paper risk (owner, 2026-10-08) |
| **ORDER** | the bot's own order for the plan, from the bot's arithmetic: copy-ready line, limit (A10), shares (A18), the runner's checks (stop ≥ 2 %, stop ≥ 4× spread), the honest stop, the halt band. Pre-market it says IBKR holds no stop (probe 2026-09-18). **Shown on REVIEW only** (owner, 2026-10-09): on WATCH, WAIT and NO there is no order block, and the card says what it waits for |
| I took it / I passed / I closed it | your call, under the order line, written to the ledger with the card you saw; the daily review scores it beside the bot. After "I took it" the card tracks the position: stop, the 1 R trail (A3), 2 R, sound and notification when one is crossed |

**The Time & Sales** is the selected name's prints from IBKR tick-by-tick
(`Last`, read against `BidAsk`), on the desk's own read-only connection
(`src/momentum_platform/datasources/ibkr_tape.py`). It follows your selection;
IBKR allows one tape request per name every 15 s, so returning to a name you
just left can take a few seconds, and the card says so.

| mark | means |
|---|---|
| ▲ green | printed at or above the ask: a buyer lifted the offer |
| ▼ red | printed at or below the bid: a seller hit the bid |
| · grey | between the bid and the ask |
| ? dim, italic | IBKR history loaded behind a new focus: no quote of that moment was read, so no side |
| bold, amber size | a big print: ≥ 10× this tape's median print, never under 2,000 shares — this desk's Approximation, not his number |
| dashed line | a gap — a reconnect, a competing login, a refusal: prints in between may be missing, and the facts restart after it |

The tag says LIVE, QUIET (no print for 30 s), STARTING, PAUSED (the feed is
stale or another login holds the data — the tape asks again when it clears) or
ERROR (IBKR refused, with its reason; click the name to retry). If IBKR refuses
only the quote stream, the prints keep coming and their side is read against
the desk's Level 1 quote — the source line says so. A locked quote (bid = ask)
names no side: those prints read "?".
A replay has no tape and says so. **Facts, not a gate**: nothing in this
repository has measured what a tape figure is worth, and none of it moves the
verdict (`docs/desk-assessment-2026-10-08.md`, "Level 2"). IBKR's tick-by-tick
needs only the Level 1 data the desk already uses, as IBKR's documentation was
reported by a web search on 2026-10-08 — if the tag reads ERROR with an
entitlement message, that report was wrong for this account.

**Level 2 — what a real book would take (researched 2026-10-09; owner: not yet).**
Ross reads the book with the tape ("level two": 264 hits in 134 live streams;
the course's minimum layout carries both). IBKR's price list, read on
2026-10-09 by a research agent, puts depth on the **live** user — non-professional
— shared to the paper user: Networks A, B and C at $1.50 each, **NASDAQ
TotalView-OpenView $16.50 plus its EDS add-on $1.00, which the API needs** —
$22.00 a month in all, $17.50 if A, B and C are already held. NYSE OpenBook
($25), ArcaBook ($11), Cboe BZX ($8) and BX TotalView ($3.50) are optional
extra books; IEX depth comes free with A, B and C. The API reads it with
`reqMktDepth(…, isSmartDepth=True)`, three depth symbols at a time by default.
Not confirmed: depth in the pre-market, depth on the shared paper login (IBKR's
paper page says fills are simulated "from the top of the book; no deep book
access"), NYSE American coverage. Sources: interactivebrokers.com
market-data pricing, the NASDAQ specialty-subscriptions page (EDS), the TWS API
market-depth page, ibkrguides article 1719 (sharing to paper). The desk's
Level 2 card is built (2026-10-09) and reads the book the moment the data is on
the account: display only — no gate, no score.

**After an update, restart the desk.** The page reads its files from disk on
every load; the desk's Python only at start. A desk left running after
`bash scripts/update.sh` serves the new page against old code — no tape, parts
of the card missing — and since 2026-10-08 the page says so in red: **RESTART
THE DESK**. `python3 scripts/day.py --restart-desk` restarts it without
stopping the bot (above, "Any hour").

The Five Pillars check lists every name the desk is holding; names **down on
the day** fold into one red line under it ("red on the day — not
candidates"). Click one to read it; the selected name always keeps its row.

**A red banner at the top** names what blinds the desk: a competing login
(10197 — your live TWS, IBKR Mobile or Client Portal on the same username took
the market data), names dropped for want of a data permission (AMEX), or the
desk not answering. Placing manual orders from a session on the same IBKR
username is what triggers 10197. IBKR's documented way to run both is a second
username on the account (Client Portal › Users & Access Rights; its market data
is billed separately) — a web search on 2026-10-08 reported this from IBKR's
article 1719; verify it in Client Portal before relying on it.

**Replaying a real day at a given minute:**
`python3 scripts/fixture_from_export.py 2026-10-06 --until 07:33 --out /tmp/f.jsonl`
then `PYTHONPATH=src python3 -m momentum_platform.dashboard.server --fixture /tmp/f.jsonl`.
The export carries no news, quotes or halts, and the RVOL baseline is
reconstructed — the fixture's header says so.

## Human-only commands

| command | when |
|---|---|
| `python3 scripts/exercise.py state` | where the exercise is |
| `python3 scripts/exercise.py report` | today's funnel, rejects, controls, replay |
| `python3 scripts/exercise.py check` | replay check alone; exit 1 on any divergence |
| `python3 scripts/exercise.py advance` | move to the next phase — refuses and lists blockers unless every gate is clear |
| `python3 scripts/exercise.py stuck` | any filled, un-exited position |
| `python3 scripts/exercise.py review` | everything so far across sessions: what kills, what is refused, verdicts, fills, controls, replay, today's risk lock |
| `python3 scripts/exercise.py ah-exit ID --confirm` | the after-hours exception: exit-only, records who confirmed |
| `python3 scripts/exercise.py accept-a1 --confirm` | records YOUR acceptance of amendment A1 (pre-market entries with no stop at the broker). Never set by code; read §5 of the pre-registration first |
| `python3 scripts/exercise.py retag-backfill --before 2026-09-08T08:06 --confirm` | one-off correction: tags the decisions recorded before the backfill tag existed (the morning of 8 September, armed on history loaded at 08:06) as backfill; dry run without `--confirm` |
| `python3 scripts/day.py --settle 2026-09-09` | the after-close block for a past day the hard stop never reached (the Mac slept, Ctrl-C): grading from the ledger's bars, replay, report, session counted once |
| `IBKR_PORT=4002 python3 scripts/backfill_tape.py 2026-09-09` | when the desk stopped early: fetches that day's 1-minute bars from IBKR (read-only) for the names decided on, resets the 'no tape' gradings, grades again. Then `--settle` |
| `python3 scripts/tape.py SYM` | the intraday workup on the desk's own tape: IBKR whenever the paper Gateway answers (header `ibkr·rt :4002 paper gateway`, real pre-market volume, live halt flag, read-only client 36), Yahoo only when no API port answers, with the reason printed. `TAPE_SOURCE=yahoo` forces Yahoo. Since 2026-09-24; before that the IBKR path never switched on |
| `python3 scripts/exercise.py missed --day 2026-09-24` | what the plans not taken went on to do, per reason — and, since 2026-09-24, **LAYER 2 · GATE BY GATE**: which of VWAP / 9 EMA / MACD / pullback-volume was red per window, what each red combination refused went on to do, and the cohort each gate ALONE refused. Upper bound, not P&L; the number an amendment is written from |
| `python3 scripts/exercise.py missed --day 2026-09-24` (KILLED PLANS BY GATE) | since 2026-09-24 evening: every Layer 1 kill scored per window, price split at $2 and $20, the sub-$2 cohort split by the penny-theme flag read from the ledger's gap-scan rows; a third exit column BE+2R (breakeven after +1 R, fixed target) beside fixed and trail everywhere |
| `Error 10089` / `Error 420 … No market data permissions for AMEX STK` | the account has no real-time data permission for NYSE American (AMEX) names; the desk drops the name (APUS, 2026-09-25) and, since that evening, never re-subscribes it. Nothing to do unless you want AMEX names on the desk, in which case add the NYSE American real-time subscription in IBKR Account Management → Market Data Subscriptions; NASDAQ names are unaffected |
| `minute history: 3 refreshes in a row timed out … paused for 5 min` | IBKR's history farm is not answering; the desk stops asking for five minutes so the decisions keep flowing on the live bars. Nothing to do |
| Ctrl-C | ends the day (since 2026-09-25 evening the desk is not restarted after it); the day is settled at the next start. After 11:30 it stops the desk alone: nothing is left to settle. Once the day has started, the command waits up to 20 min for the Gateway's API port instead of failing |
| `python3 scripts/day.py --restart-desk` | after `bash scripts/update.sh` while a day or the desk alone runs: that run's desk restarts on the new code; the runner is not touched (2026-10-08) |
| `python3 scripts/backtest_history.py --sample 300` then without `--sample` | the desk's own rules over the 25,716 gapper-days 2016–2026 WITH pre-market volume (Alpaca SIP, the headline keys in `.env`), net of costs, per year and per window, a walk-forward optimizer, and `--ledger data/journal.sqlite` for forecast vs actuals on your live trades. Runs on the Mac; the cloud side has no feed with pre-market volume |
| the desk dies mid-morning | since 2026-09-24 evening `day.py` waits for the Gateway port (up to 20 min) and restarts the desk itself, up to five times; the runner keeps managing any open position. If the Gateway shows the paper-trading disclaimer, click it |
| `IBKR_PORT=4002 python3 scripts/day.py --probe-orders` | the only way the day command runs the pre-market stop probe, which places and cancels an unfillable paper bracket. Off by default: an observational day dispatches nothing order-shaped |
| `python3 scripts/watch_bot.py` | **watch the bot live**, in a second tab (since 2026-10-09). It opens the ledger read-only and prints each step once, as it happens: ARMED / REFUSED (with the rule) / TAKEN, SENT, FILLED (slippage vs the trigger), every bot event (stop watch, trail, sell sent), EXIT (R and $), LOCK. A status line every minute shows positions with their R now, today's R and the risk gate. `S6 ✓` / `S3 ✓` marks a plan a shadow strategy would take. `--all` adds the cascade's kills. Ctrl-C stops the watcher, never the bot |
| `python3 scripts/shadow_record.py` | the **shadow strategies' paper track record** (since 2026-10-09). S6 is the month study's best found: stop ≥ 3 % + $2–20 + regular hours + above VWAP + lighter pullback volume + still rising. S3 is its robust core: stop ≥ 3 % + $2–20 + regular hours. Both exit at break-even after 1 R, then 2 R. Every plan the desk armed is judged and scored on the desk's own bars, net of costs. Logged, never traded: the bot's rules are unchanged. On the desk, a card shows `shadow S6 ✓` when one would take the plan. Read the record at 30 and 100 trades a strategy, not before (`research/month-study/REPORT.md`) |
| no GitHub credentials on the Mac | the day's export cannot be pushed. Since 2026-10-09 a failed push undoes its local commit and moves the day folder to `~/day-trading-exports/<day>/`, so the next morning's pull is not refused. For a review, zip that folder and upload it to the session. A range: `python3 scripts/day_export.py --since 2026-10-09 --board-bars --out ~/Desktop/export` |

## Optional: start it for you

`bash scripts/install_daily.sh` installs a macOS launchd agent that runs
`scripts/day.py` at 06:55 ET on weekdays with `IBKR_PORT=4002` and logs to
`~/Library/Logs/day-trading-bot/`. The Gateway login stays yours.
`bash scripts/install_daily.sh --remove` takes it out.

### Watching a day the agent started

Nothing appears in a terminal: the day runs in the background. Its lock
refuses a second `day.py` ("a trading day is already running … pid N") — since
2026-10-08 that answer gives the desk's link and names a desk on older code —
and `kill -INT N` is the only clean way to stop it early. The agent's run no
longer ends at 11:32: the desk stays up and the run starts the next trading
day itself.

| to see | run (in the repo, any terminal) |
|---|---|
| the executor's log — REFUSED, TAKEN, fills, exits, stop enforcement — live | `tail -f ~/Library/Logs/day-trading-bot/day.out.log` |
| errors only | `tail -f ~/Library/Logs/day-trading-bot/day.err.log` |
| **every** plan, including the ones the stock filters KILL (they never reach the executor log), plus orders, fills, exits and order events, live | `python3 scripts/watch.py` |
| the desk itself | http://127.0.0.1:8787/ |

Ctrl-C in these windows stops the viewer, never the bot. `watch.py` opens
the ledger read-only and needs nothing but the standard library, so it also
runs against an older checkout. The agent runs `git pull` before starting: a
local file that a pull would overwrite (an untracked report under
`research/`) makes it run yesterday's code — move such a file aside.

## If something looks wrong

- **Desk shows no plans all morning** → `exercise.py report`: the REJECTS
  block says which gate killed each name. Suppressed is counted, not hidden.
- **`check` returns 1** → stop trading; the log or the code drifted. The
  divergent decisions are listed with recorded vs replayed verdicts.
- **A position after 16:00** → the runner flagged it and printed the
  `ah-exit` command. Nothing sells until you confirm.
- **`exercise.py stuck` shows a row with status `ExitPending`** → a sell was
  sent (monitored stop, hard-stop flatten or `ah-exit`) and its fill has not
  been read back yet. The next runner sync closes it at the real fill price;
  if the runner is gone, check the position in the Gateway.
- **The runner restarted mid-morning** → it adopts its open orders from the
  ledger and matches them at the broker by IBKR's permanent id. An order
  whose acknowledgement was never saved is found by its reference (the
  decision id on every leg) or marked `UNRESOLVED` for you; it is never sent
  again. Nothing is placed twice, whatever the restart count.
- **A `start UNRESOLVED intent` or `RECONCILE` line in the runner output** →
  the ledger and the broker disagree about a position. New entries are
  blocked until you look: `exercise.py stuck`, then the Gateway's order and
  position windows.
- **`phase A: the exercise is log-only — --trade is refused`** → the
  runner will not trade before `exercise.py advance` has moved the exercise
  to phase B. This holds at the execution boundary, not only in the day
  command.
- **`another runner already holds …lock`** → a runner is already attached to
  this ledger. Two would claim the same decision; the second refuses.
- **Probe says `queued`** → pre-market entries are unprotected by design
  (`src/execution/policy.py`); phase C needs your written acceptance in
  `docs/preregistration.md` §5.

*Paper only. Every figure in the reports is selection quality, never edge
(`research/momentum-replication/reports/2026-08-regime-filter.md`).*
