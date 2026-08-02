# Daily recap transcripts

Separate from `../transcripts/`, which holds the 257-video **teaching** shortlist
selected by `scripts/pipeline/00_select_teaching.py`. That selection filtered
*for* instructional content and therefore filtered *out* the daily recaps — so
until now the corpus contained the strategy as taught and nothing about the
trades actually taken.

These are the recaps covering the week of 2026-07-27, the same week the
simulation in `research/momentum-replication/` replays.

| Video | Title |
|---|---|
| `83Yuliq1vHA` | Record Breaking Green Day! |
| `Zj0DYfQilso` | Biggest Red Day... |
| `1ml6zHikpsE` | Max Loss Red Day... |
| `SuY-q_OWMHw` | Taiwan Stock with Breaking News Goes up 177% |
| `p73Vmwgg64c` | THIS is why today was choppy... |

## Why these matter

`README.md` in the handoff package says a faithful test needs **labelled
examples of setups he demonstrably took**. These are those labels: each recap
names the tickers traded and walks the entries. They are the calibration set,
and they cost nothing to fetch.

## Dating caveat

`../data/README.md` warns that index dates are synthetic below year
granularity. For recent uploads the relative labels YouTube returns ("3 days
ago") convert accurately, so these are approximately right — but the recaps
themselves are a numbered series ("day 26", "day 27" of a $2,000 small-account
challenge) and one opens "back at it today after the red day". **Use the
sequence, not the index date, to map a recap to a session.**

## Fetching more

```bash
pip install yt-dlp
python scripts/fetch_subtitles.py --index knowledge-base/data/daytradewarrior_videos.json \
                                  --out-dir knowledge-base/recaps
```

The existing fetcher works unchanged; the recaps were simply never in the
shortlist it was pointed at.
