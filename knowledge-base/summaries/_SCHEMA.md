# Summary schema

One file per transcript: `knowledge-base/summaries/<video_id>.md`.

The purpose of these files is to make 159 hours of speech searchable and to
locate where each mechanical rule was stated. They are an index, not a
replacement for the transcript — when a rule matters, the timestamp sends you
back to the source.

Every file uses exactly this structure. The YAML frontmatter is parsed by
`scripts/pipeline/06_build_index.py`, so its keys and types are fixed.

```markdown
---
video_id: dQw4w9WgXcQ
title: "How to Trade the Bull Flag Pattern"
url: https://www.youtube.com/watch?v=dQw4w9WgXcQ
duration_min: 27
teaching_class: howto
topics: [bull-flag, entries, stop-loss, scanners]
has_rules: true
---

# How to Trade the Bull Flag Pattern

## Summary

Two to four sentences: what the video teaches and who it is aimed at. State the
subject, not the fact that it is a video.

## Mechanical rules

Concrete, codeable statements — entry triggers, exits, sizing, filters, limits.
One bullet each, with the timestamp where it is stated.

- [00:04:12] Enter on the first candle that makes a new high after the pullback.
- [00:11:38] Stop goes at the low of the pullback, never wider.

Write `_None stated._` if the video states no codeable rule.

## Setups and patterns

Named setups discussed, one line each with a short definition.

- **Bull flag** — sharp move up, sideways consolidation, break of consolidation high. [00:03:50]

## Indicators, tools, platforms

Anything referenced by name: MACD, VWAP, 9 EMA, specific scanners, brokers,
platforms. One line each, with what it is used for.

## Numbers and thresholds

Every specific figure: float sizes, price ranges, percentage gains, volume
minimums, position sizes, account sizes, win rates. Quote the figure and give
its timestamp. These are the values a backtest needs.

- [00:19:02] Float under 20 million shares.
- [00:22:47] Looks for 5x relative volume.

## Claims needing verification

Performance figures, win rates, and any assertion presented as fact without
evidence. Record the claim, do not evaluate it.

- [00:31:15] Claims a 68% win rate on this setup over an unspecified period.

## Caption quality notes

Note where auto-captions are clearly garbled, especially misheard tickers or
numbers, so a later reader does not trust a corrupted figure.
```

## Rules for whoever writes these

1. **Timestamps are mandatory** on every rule, number, and claim. They are the
   entire point. Copy them from the `[HH:MM:SS]` markers in the transcript.
2. **Do not invent.** If the video does not state a stop-loss rule, the section
   says `_None stated._` An empty section is a finding; a fabricated one is a
   corrupted index.
3. **Separate claim from rule.** "I made $40,000 on this setup" is a claim.
   "Enter on the break of the high" is a rule.
4. **Captions are auto-generated** — no punctuation, and tickers and numbers are
   often wrong. Where a figure looks garbled, record it and flag it in the
   caption quality section rather than silently correcting it.
5. **`topics`** are lowercase kebab-case tags, 3 to 8 per video, drawn from the
   vocabulary the channel actually uses (`bull-flag`, `gap-and-go`, `vwap`,
   `position-sizing`, `risk-management`, `scanners`, `psychology`, `taxes`,
   `brokers`, `small-account`, `short-selling`, `candlesticks`, `moving-average`,
   `float`, `catalyst`, `pre-market`).
6. **`has_rules`** is `true` only if the Mechanical rules section has at least
   one entry.
7. Keep the whole file under roughly 400 lines. This is an index, not a
   retelling.
