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
