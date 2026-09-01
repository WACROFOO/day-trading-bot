# Connecting the workstation to Alpaca — step by step, free

> Written for someone who has not done this before. Every step says what to
> type, what you should see, and what to do when you see something else.
> Nothing here costs money and nothing places a real order.

## Where to run this

Everything below runs **on your own computer**, in a terminal, in the folder
that holds `README.md`. It cannot be done for you from a cloud session: those
containers sit behind a proxy that blocks `api.alpaca.markets` outright, and
they are wiped when the session ends, so any `.env` written there disappears
with it. Your keys belong on your machine and nowhere else.

---

## The fastest path (one command)

If you would rather not edit files by hand:

```bash
cd day-trading-bot
bash scripts/setup.sh
```

It finds your Python, asks for the two keys (the secret stays hidden as you
type or paste it), writes `.env` with owner-only permissions, proves git is
ignoring it, runs the test suite, and finishes by running the connection check
in Step 3. If anything fails it tells you which of the two usual causes it is.

Steps 1–3 below are the same thing done by hand, so you can see what the script
did. Read them either way — Step 4 onward is the part that matters daily.

---

## Before anything: the two rules about keys

1. **The secret key is shown once.** When Alpaca generates a pair, copy both
   immediately. If you lose the secret, you regenerate the pair — you cannot
   look it up later.
2. **Never paste the secret anywhere except your `.env` file.** Not in a chat,
   not in a screenshot, not in a file you commit. If it has ever been visible
   somewhere else, regenerate the pair; it takes ten seconds and costs nothing.

The Key ID (starting `PK`) is not enough to authenticate on its own, but treat
the pair as one credential.

---

## Step 1 — get the keys (5 minutes, in your browser)

1. Go to **https://alpaca.markets** and create a free account.
2. Open the dashboard and make sure the toggle at the top-left says
   **Paper Trading**, not Live. Paper is fake money.
3. In the right-hand panel find **API Keys** → **Generate New Key**.
4. You now see two values. Copy both:
   - **Key ID** — starts with `PK` for paper keys
   - **Secret Key** — a longer string, shown only this once

> **You should see** a Key ID beginning `PK`. If it begins `AK` you generated
> live keys — switch the toggle to Paper and generate again.

---

## Step 2 — put the keys in a file the code can read (2 minutes)

In a terminal, from the project folder:

```bash
cd day-trading-bot
cp .env.example .env
```

Open `.env` in any text editor and replace the placeholders:

```
ALPACA_KEY_ID=PK................
ALPACA_SECRET_KEY=................................
ALPACA_FEED=iex
ALPACA_TRADING_BASE=https://paper-api.alpaca.markets
```

Save and close.

> **Why a file?** Because `.env` is listed in `.gitignore`, so it can never be
> committed by accident. The code reads it automatically — there is nothing to
> install and no library involved.

Confirm git is ignoring it:

```bash
git status --short
```

> **You should see** no mention of `.env`. If `.env` appears, stop and tell me
> before committing anything.

---

## Step 3 — prove the connection works (1 minute)

```bash
python scripts/verify_alpaca.py
```

This runs nine checks and prints PASS, WARN or FAIL for each with the fix.

> **You should see** PASS on credentials, account, clock, daily history and
> snapshots. WARN on the intraday and news checks is normal outside market
> hours — it means "nothing has traded yet today", not "broken".

Common results and what they mean:

| What you see | What it means | What to do |
|---|---|---|
| FAIL: ALPACA_KEY_ID missing | `.env` not found or not filled in | Check you are in the project folder and saved the file |
| FAIL: HTTP 401/403 | Key and secret do not match, or live keys on the paper endpoint | Regenerate a **paper** pair and paste both again |
| FAIL: could not reach Alpaca | Network, VPN or company proxy | Try another network; corporate Wi-Fi often blocks this |
| WARN: no minute bars today | Market closed, or before 04:00 ET | Normal. Re-run during a session |
| WARN: no headlines | These symbols are quiet | Normal. Try a name that is moving |
| FAIL: HTTP 429 | Too many requests | Wait a minute; scan fewer symbols |

Do not continue until the first five checks pass.

---

## Keeping up to date

```bash
bash scripts/update.sh
```

It stashes any uncommitted edits, snapshots your commits to a `backup-…`
branch, fetches with retries, and moves you onto the latest version — then
tells you what changed. Your `.env` is git-ignored, so no update can touch
your credentials.

> **A warning about copying commands from chat.** macOS uses zsh, and an
> interactive zsh does **not** treat `#` as a comment. Pasting a block like
> `# 1) do this` gives `zsh: parse error near ')'` and nothing runs. Copy
> command lines only, never the commented explanations around them.

---

## Step 4 — start the desk

```bash
bash scripts/start.sh
```

That is the whole command, and it is the one you will type every day.

It checks Alpaca first, then does the right thing:

| What it finds | What it does |
|---|---|
| Live feed working | opens the desk on today's real IEX data |
| Keys missing | tells you to run `setup.sh`, opens the recorded session |
| Keys rejected | tells you to regenerate the pair, opens the recorded session |
| Network blocked | tells you it is the network, **not** your keys, opens the recorded session |
| Port 8787 busy | moves to 8788 and says so |

**The desk always comes up.** If the live feed is unavailable you get a
recorded trading session instead — every card, chart, scanner and the verdict
engine behave identically, only the data is from a saved day. That is the
right place to learn the platform while a connection problem gets sorted.

Variations:

```bash
bash scripts/start.sh AAPL,TSLA   # live, symbols you name
bash scripts/start.sh --scan      # live, whatever passed the pillars today
bash scripts/start.sh --replay    # recorded session on purpose, no network
```

### The one thing that trips everybody up

The last thing the script prints is the address:

```
Open this in your browser:  http://127.0.0.1:8787
```

`127.0.0.1` means **this computer**. The page exists only while that terminal
window is running the script. So:

- **Leave the terminal window open.** Closing it, or pressing Ctrl-C, stops the
  desk and the browser tab immediately goes dead.
- **Open the address in a browser on the same computer.** It is not a website;
  another device on your wifi cannot reach it, and neither can anyone else.
- **"This site can't be reached" means nothing is running**, not that something
  is broken. Go back to the terminal, run `bash scripts/start.sh`, wait for the
  address to print, *then* open the browser.

> **You should see** the header read `IEX` on live data, or `REPLAY` on a
> recorded session. Press Play to walk the session forward minute by minute.

---

## Step 4b — doing it by hand (optional)

## Step 4 — see real charts in the workstation (2 minutes)

Pick any two liquid symbols to start:

```bash
PYTHONPATH=src python -m momentum_platform.dashboard.server --alpaca AAPL,TSLA
```

Open **http://127.0.0.1:8787** in your browser.

> **You should see** the header say `IEX` instead of `REPLAY`, real candles on
> the 1-minute chart, and real headlines in the catalyst card if those symbols
> have news. Press Play to walk through the session minute by minute.

If the page loads but the charts are empty, the market has not traded today
yet. Run it again after 09:30 New York time, or use yesterday's session by
running the same command after the close.

---

## Step 5 — scan the whole market for today's movers (2 minutes)

```bash
python scripts/alpaca_watchlist.py --top 8
```

This scans every tradable US equity — **NASDAQ and NYSE**, roughly 11,000
names — and applies the pillars that can be computed from free data: price
$2–$20, gain ≥ 10%, relative volume ≥ 5×, and a minimum volume floor.

> **You should see** a short table of survivors, then a comma-separated list on
> the last line. Zero survivors is a normal morning — do not widen the filter
> to manufacture a candidate.

Then feed the list straight into the desk:

```bash
PYTHONPATH=src python -m momentum_platform.dashboard.server \
  --alpaca $(python scripts/alpaca_watchlist.py --top 6)
```

That single line is your morning: scan the market, load the candidates, open
the browser.

---

## Step 6 — what you now have, and what is still missing

| Card | Data now | Quality |
|---|---|---|
| Five Pillars Scan | Alpaca IEX bars + snapshots | Real. Float pillar reads `unknown` |
| Running Up | Alpaca IEX bars | Real |
| HOD Momentum | Alpaca IEX bars | Real. Branch label needs float |
| 1m / 5m charts | Alpaca IEX bars | Real |
| 10-second chart | — | Needs a tick stream; shows an explicit note |
| Daily chart | Alpaca daily bars | Real, split-adjusted |
| Quote · supply · risk | Alpaca snapshots | Real except float |
| Catalyst | Alpaca news | **Real headlines with real timestamps** |
| Level 2 | — | Simulated and labelled; needs a paid depth licence |
| Setup verdict | everything above | Real, with the float pillar failing honestly |

### The one caveat you must understand

The free feed is **IEX**, a single exchange. It is genuinely real-time — a large
upgrade on the 15-minute delay you had — but IEX carries only a slice of total
US volume. So:

- **Prices, highs, and percentage moves are trustworthy.** IEX prints the same
  prices as everywhere else.
- **Absolute volume is understated.** A stock showing 300,000 shares on IEX may
  have traded several million across all venues.
- **Relative volume still works**, because the scanner divides today's IEX
  volume by the average of prior days' *IEX* volume. Both sides come from the
  same venue, so the ratio survives even though neither number is the
  consolidated one. It is labelled `iex` everywhere it appears.

Do not compare an IEX volume figure with a number you read on a website that
uses consolidated volume. They are different measurements.

---

## Step 7 — filling the remaining gaps for free

**Float** — no free API publishes reliable float. Until you pay for one:
look the symbol up once (your broker, the company's SEC filings, a free finance
site) and note it. The platform shows `unknown` rather than guessing, and the
supply pillar fails with a visible reason, which is the honest behaviour.

**Halts** — Nasdaq publishes a free halt RSS feed that updates once a minute.
Worth wiring next; it is the cheapest real risk protection available.

**Level 2** — needs a paid depth licence. You already decided to defer this;
that remains the right order.

**Paper orders** — your Alpaca paper account can accept simulated orders
through the same credentials. The repository already has a risk-gated paper
simulator, so this is a later convenience, not a gap.

---

## Step 8 — your daily routine, now that it is wired

```bash
# 07:00–09:00 ET — build the list
python scripts/alpaca_watchlist.py --top 8 --save data/watchlist.txt

# 09:00 ET — open the desk on those names
PYTHONPATH=src python -m momentum_platform.dashboard.server \
  --alpaca $(cat data/watchlist.txt)

# after 16:00 ET — replay the day you just watched
#   same command; scrub back to 09:25 and press Play
```

The rest of the routine — what to do at each hour, and the 30-session
progression — is in `docs/daily-operating-guide.md`.

---

## When something breaks

| What you see | What it actually means |
|---|---|
| **This site can't be reached** at `127.0.0.1:8787` | No desk is running. Start it in a terminal with `bash scripts/start.sh`, wait for the address to print, then reload. |
| The page went blank mid-session | The terminal was closed or Ctrl-C was pressed. Start it again. |
| Header says `REPLAY` when you wanted live | The launcher already told you why, higher up in the terminal. Scroll up and read that line. |
| `certificate verify failed` | **Not a network problem and not a bad key.** Python from python.org carries its own certificate store and ignores the macOS keychain. Open Applications → your Python 3.x folder → double-click `Install Certificates.command`, then retry. Do not regenerate your keys. |
| `Could not reach Alpaca` | Network, VPN or firewall. **Your keys are fine.** Try home wifi. |
| `401` / `403` from Alpaca itself | The key pair is wrong. Regenerate a paper pair, re-run `setup.sh`. |
| Charts empty on live data | The market has not traded yet today. Normal before 04:00 ET. |

Run `python scripts/verify_alpaca.py` for the layer-by-layer breakdown. It
isolates which one failed: credentials, network, entitlement, or simply a
closed market. Ninety percent of problems are one of:

1. `.env` in the wrong folder — it belongs next to `README.md`;
2. live keys used against the paper endpoint;
3. the market being closed;
4. a symbol that does not trade on IEX.

If the script passes and the dashboard still looks wrong, that is a bug in the
platform rather than in your setup — say so and paste the terminal output.
