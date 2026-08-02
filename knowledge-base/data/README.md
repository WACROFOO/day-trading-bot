# Data

Raw reference data collected for the knowledge base. Information gathering only — nothing here has been used for strategy development or backtesting.

## `daytradewarrior_videos.json`

Metadata index of the Ross Cameron / Warrior Trading YouTube channel (`@DaytradeWarrior`, `UCBayuhgYpKNbhJxfExYkPfA`).

Collected with `scripts/scrape_youtube_index.py` (yt-dlp, flat extraction). Metadata only: video id, title, URL, duration, view count, timestamp. No video content or transcripts.

**Snapshot:** 2,211 videos, 2014–2026, ~756 hours of runtime, 138.9M total views.

### ⚠️ Upload dates are approximate — do not trust below year granularity

Flat extraction does not return true upload dates. It returns YouTube's relative labels ("2 years ago"), which yt-dlp converts into a synthetic timestamp.

Consequence: 1,867 of 2,211 videos carry a date of July 31, and only 26 distinct month-day combinations exist across twelve years.

- **Year:** approximately correct, usable for coarse trends.
- **Month and day:** synthetic. Not usable.

Do not join these dates against market sessions or price data. Exact dates require a per-video metadata fetch (~2,211 requests).

### Regenerating

```bash
python scripts/scrape_youtube_index.py
python scripts/summarize_video_index.py
```

## `daytradewarrior_streams.json` — the tab the corpus missed

`daytradewarrior_videos.json` was scraped from `@DaytradeWarrior/videos`. YouTube
files live broadcasts under a **separate `/streams` tab**, and none of them were
in it: **480 streams, 0 of which appear among the 2,211 indexed videos.**

| | |
|---|---|
| streams | 480 |
| of those, "Day Trading Morning Show" episodes | 325 (~214 hours) |
| an hour or longer | 84 |
| two hours or longer | 18 |
| longest | 4h32m, `YuNvqwJftVY` |

This matters beyond completeness. `../../research/momentum-replication/NEXT-STEPS.md`
§5 concludes the replication fails on entry **timing**, and says the corpus
cannot settle it because the teaching videos explain setups after the fact. The
Morning Show is the missing register: he is narrating decisions in real time,
before the outcome is known, which is the only place the corpus contains
unhindsighted entries.

Fetched with:

```bash
yt-dlp --flat-playlist -J https://www.youtube.com/@DaytradeWarrior/streams
```

Fields are `id`, `title`, `duration`, `views`. Upload dates need a per-video
metadata call, as with `july_meta.json` — the flat listing does not carry them.
