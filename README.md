# Day Trading Bot

An attempt to mechanically implement and honestly test the Ross Cameron /
Warrior Trading small-cap momentum strategy, built on ~2,700 transcribed videos
and free 1-minute market data.

## State of play — read this first

**The strategy has not been shown to work, and neither has the opposite.** The
implementation now matches the documented rules closely (20 recorded defects
found and fixed along the way), and over 17 real sessions of July 2026 it
produces 15 trades at −0.43R expectancy. That is not a verdict on the strategy:
the live streams show his entries happen on a **10-second chart** and off
**Level 2**, neither of which 1-minute OHLCV data can represent. The full
argument: `research/momentum-replication/reports/`.

The measurement that matters most so far: of the tickers he demonstrably traded
in July 2026, the engine agrees with him on **22%** (`diagnostics/calibrate.py`)
— up from 4% before the last bug hunt. That agreement number, not P&L, is the
project's steering metric.

## Map

| Folder | What it is |
|---|---|
| `knowledge-base/` | Everything extracted from the source: transcripts, summaries, recaps, live streams, and the **canonical strategy documents** (`strategies/`) |
| `research/momentum-replication/` | The implementation and its test harness: engine, pipelines, diagnostics, dated reports, defect history |
| `scripts/` | The corpus tooling: scraping, transcription, claims database, search, stream mining |
| `data/` | `claims.db` — 7,937 tagged claims, each deep-linked to a video timestamp |
| `src/paper_trading/` | A manual paper-trading platform (Streamlit) for practising the strategy by hand |
| `tests/` | Tests for the paper-trading platform and scanner |
| `archive/` | Superseded work, kept for the record — **do not build on it** |

Every folder has a `README.md` saying what is in it.

## The three entry points

**Study the strategy** → `knowledge-base/strategies/PARAMETERS.md`, and read
its §13 (misreading traps) before believing any single rule. Search the raw
evidence with:

```bash
python scripts/search.py "profit target"           # claims, deep-linked
python scripts/mine_streams.py timing              # live-stream evidence by topic
```

**Run the replication** → `research/momentum-replication/RUN.md`. Start with
`reports/README.md` for what has already been established, `HISTORY.md` for
the 20 defects already found (so the same ground is not covered twice), and
`NEXT-STEPS.md` for what is genuinely open.

**Trade it by hand** →

```bash
pip install -r requirements.txt
streamlit run src/paper_trading/app.py
```

Scanner, charts, risk-based order ticket, journal, and the five daily risk
rules with a lockout latch. Manual only — there is no automated bot, and given
the research findings there should not be one yet.

## House rules

1. Claim and evidence stay separate; marketing numbers are not results.
2. Every rule cites a video id and timestamp; when documents and corpus
   disagree, the corpus wins.
3. No P&L number is a result until the harness measuring it has been audited —
   the sign has flipped on identical data eight times in this project.
4. Superseded work moves to `archive/`, never gets silently edited.
