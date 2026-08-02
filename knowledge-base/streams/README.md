# Live stream transcripts

Separate from `../transcripts/` (the 257-video teaching shortlist) and
`../recaps/` (the after-the-close daily wrap). This is the third register and
the only one recorded **before the outcome is known**.

The teaching videos explain a setup with the chart already finished. The recaps
narrate the day that just ended. Both are hindsight by construction. A live
stream is him committing to an entry, a size and a stop while the next candle
does not exist yet - which is the only place the corpus can answer a question
about *timing*.

| | |
|---|---|
| streams on the channel's `/streams` tab | 480 |
| selected as live trading (>= 25 min, not seminars) | 296 |
| transcribed here | see `ls *.txt \| wc -l` |
| words | ~1,096,000 at 266 streams |

None of these were in `../data/daytradewarrior_videos.json`, which was scraped
from the `/videos` tab only. The full stream index is
`../data/daytradewarrior_streams.json`.

## Reading them

```bash
python scripts/mine_streams.py --list       # the topics and why each matters
python scripts/mine_streams.py timing       # one topic, with deep links
```

Each topic is a regex tied to an open question in
`../../research/momentum-replication/NEXT-STEPS.md`. Hits print the surrounding
seconds, because a keyword match on caption text is a pointer, not evidence -
read the context before believing it.

## Caveats

- **Auto-captions.** Tickers and prices are garbled routinely ("1282" for
  $12.82, "cere" for CERE). Prices in these transcripts are frequently
  quoted without the decimal point - "added at 710" means $7.10.
- **No dates below the metadata call.** The flat listing carries no
  `upload_date`; `../../research/momentum-replication/data/stream_meta.json`
  has the real ones where the fetch succeeded.
- **These are 2021–2023.** 47 from 2021, 174 from 2022, 45 from 2023, one from
  2026 — the live Morning Show largely stopped after 2023. None overlap the
  2026-07 bar-data window, so they are evidence about *method*, not a labelled
  set to score the engine against. Check anything time-sensitive against
  `../recaps/`, which is June–July 2026.
- **Selection is not random.** Titles were filtered for live trading, and
  titles skew toward good days ("+$28k", "Green Day"). Anything counted across
  these files inherits that bias. Use them for *what he does*, not for *how
  often it works*.
