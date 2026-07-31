# Transcripts

Auto-generated English captions for the instructional videos on the
DaytradeWarrior channel. 257 videos, ~159 hours, one `<video_id>.txt` per video.

These are the raw input to the extraction pipeline. They are committed so that
every rule in `../strategies/` can be traced back to the exact sentence and
timestamp it came from, and so the corpus stays fixed while the extraction code
changes around it.

## Format

```
# <video title>
# https://www.youtube.com/watch?v=<video_id>
# duration_sec: <n>

[HH:MM:SS] line of speech
```

Timestamps are the caption cue start times, so any extracted rule can cite the
moment it was stated.

## What is here, and what is not

Selected by `scripts/pipeline/00_select_teaching.py` from the 2,211-video
channel index, keeping three title classes:

| class      | n   | what it is                                        |
|------------|-----|---------------------------------------------------|
| `howto`    | 158 | step-by-step explanations of a technique          |
| `rules`    | 85  | named strategies, setups, patterns, scanners      |
| `mistakes` | 14  | post-mortems, which state rules by their breach   |

Excluded: the ~1,000 daily P&L recaps ("+$35,347 in 3 Hours"), watchlists and
game plans, and anything under 8 minutes. Those narrate one session and state
few reusable rules. See the selection script for the exact patterns.

## Caveats

1. **Auto-captions, not a transcript service.** No punctuation, no speaker
   labels, and ticker symbols and numbers are frequently wrong. Never trust a
   figure read out of these files without checking it against the video.
2. **This is one trader's claims, not verified fact.** Everything here is
   subject to the standing rules in `../README.md` — in particular that a
   documented strategy is not a validated one.
3. **Reproducible.** Regenerate with:

   ```bash
   python scripts/pipeline/00_select_teaching.py
   python scripts/fetch_subtitles.py \
       --index knowledge-base/data/teaching_shortlist.json \
       --out-dir knowledge-base/transcripts \
       --workers 2 --sleep 2.0
   ```

   Keep `--workers` at 2. Higher concurrency triggers a bot check that YouTube
   reports as "no captions available", which silently poisons the failure list
   with videos that are actually fine.
