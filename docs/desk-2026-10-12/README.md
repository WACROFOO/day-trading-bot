# desk-2026-10-12 — the Level 2 montage and the buy/sell tape, before and after

The write-up is `../desk-2026-10-12.md`. Every image here is **synthetic**: the
account has no depth subscription yet and a replay has no tape, so the book and
the prints were built by the desk's own models (`src/momentum_platform/depth.py`
`DepthBook`, `src/momentum_platform/tape.py` `TapeBook`) around the replay's
last IPDN close and injected into the page. Both cards carry a dashed
"SYNTHETIC — test data, not IBKR" label in their header. The desk under them is
the replay of 2026-10-06 at 09:24 ET (`scripts/fixture_from_export.py`).

| file | what |
|---|---|
| `before_level2_SYNTHETIC.png` | the card at `5906fba`: the vertical ladder, asks above the inside, bids below, centred on the inside quote — the bids run off the bottom of the card |
| `after_level2_SYNTHETIC.png` | the montage: bids on the left, asks on the right, each side's best price on top; MMID · Bid · Size and MMID · Ask · Size; one colour per price level, the same on both sides (the inside yellow, then green, cyan, blue, violet); the 6.53 level that holds 20,200 shares marked huge with an amber edge and named in the event line |
| `before_tape_SYNTHETIC.png` | the tape at `5906fba`: time, price, size and a ▲ / ▼ mark, under a sentence of explanation |
| `after_tape_SYNTHETIC.png` | the standard tape: TIME · PRICE · SIZE · EXCH · B/S, newest on top, B green (at the ask), S red (at the bid), the colour key on the first line, the 60-second line in buys and sells, the 9,000-share print bold |
| `before_desk_SYNTHETIC.png`, `after_desk_SYNTHETIC.png` | the whole desk, 1920 × 952: the right column is the decision card, the book, the tape |
