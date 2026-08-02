# Daily recap transcripts

Separate from `../transcripts/`, which holds the 257-video **teaching** shortlist
selected by `scripts/pipeline/00_select_teaching.py`. That selection filtered
*for* instructional content and therefore filtered *out* the daily recaps — so
until now the corpus contained the strategy as taught and nothing about the
trades actually taken.

These now cover **all of June and July 2026** — 68 videos, each with the real
`upload_date` returned by a per-video metadata call rather than the index's
synthetic date. That is what turns them from anecdotes into labelled sessions.

| Span | Videos |
|---|---|
| 2026-06-01 .. 2026-06-30 | 32 |
| 2026-07-01 .. 2026-07-29 | 36 |

Titles and dates: `research/momentum-replication/data/july_meta.json`.

## Why these matter

`README.md` in the handoff package says a faithful test needs **labelled
examples of setups he demonstrably took**. These are those labels: each recap
names the tickers traded and walks the entries. They are the calibration set,
and they cost nothing to fetch.

## Dating — resolved

`../data/README.md` warns that index dates are synthetic below year
granularity, and earlier work here mapped recaps to sessions by their numbered
sequence ("day 26", "day 27" of the $2,000 small-account challenge). That is no
longer necessary: `upload_date` from the metadata call is real, and each file's
header carries it. Mapping is now by publication convention — a recap is posted
after the close, so a weekday upload is that session and a weekend upload is
the Friday before; `Watch List for MONDAY` videos are previews and map forward.

## What they were used for

`research/momentum-replication/reports/2026-07-july-calibration.md` — the first
measurement of the engine against something outside itself. 61 session-ticker
pairs across 14 sessions. Two caveats worth carrying:

- **Auto-captions garble spelled-out tickers.** One recap renders INLF as INFL,
  INLX and INFS in the same paragraph. `diagnostics/calibrate.py` repairs only
  edit-distance-1 matches to a symbol that was on the tape that day, and
  reports repaired and exact counts separately.
- **"Named in a recap" is not "traded that session."** Recaps review prior days
  and preview watchlists, so the pair count is an upper bound on his trades.

## Fetching more

```bash
pip install yt-dlp
python scripts/fetch_subtitles.py --index knowledge-base/data/daytradewarrior_videos.json \
                                  --out-dir knowledge-base/recaps
```

The existing fetcher works unchanged; the recaps were simply never in the
shortlist it was pointed at.
