# warrior-blog — the written corpus

**2,063 articles, ~3,127,215 words**, stored in full.

A second register independent of `transcripts/`, `recaps/` and `streams/`:
edited, dated prose rather than auto-captioned speech.

Articles are filed by **content**, not URL slug — see
`scripts/reclassify_blog.py`. Classification is keyword scoring with a
minimum-confidence threshold, so expect roughly a 10% error rate and
search across categories rather than trusting one.

`URLS.json` is the manifest of all 2,162 source URLs. The 99 with no
extractable text are itemised in `NOT-FETCHED.md`:
**2,162 = 2063 stored + 99 unextractable.**

Search: `python scripts/corpus.py "<term>"` or the `warrior-corpus` skill.

| category | articles | words | what is in it |
|---|---:|---:|---|
| [recaps](recaps/README.md) | 538 | 1,333,773 | Written trade recaps — dated session write-ups stating entries, exits and P&L  |
| [other](other/README.md) | 356 | 398,474 | Genuinely residual: too short, too mixed, or off-taxonomy. Search it explicitl |
| [reviews](reviews/README.md) | 136 | 301,395 | Broker, tool and service reviews. |
| [terminology](terminology/README.md) | 124 | 78,538 | Definitional articles — "what is X", "X explained". |
| [business-finance](business-finance/README.md) | 121 | 103,426 | Investing and personal finance: retirement, dividends, ETFs, macro, taxes. |
| [core-strategy](core-strategy/README.md) | 104 | 110,992 | Setups and entries: momentum, bull flag, gap-and-go, micro pullback, ABCD, fla |
| [risk-psychology](risk-psychology/README.md) | 77 | 101,171 | Risk management, position sizing, stop losses, discipline, FOMO, journaling. |
| [tools-platforms](tools-platforms/README.md) | 75 | 92,459 | Brokers, scanners, charting software, hotkeys, Level 2. |
| [options](options/README.md) | 67 | 74,456 | Options strategies, the greeks, spreads. |
| [rules-regulation](rules-regulation/README.md) | 67 | 79,146 | PDT, margin, wash sales, halts, SEC/FINRA rules. |
| [market-news](market-news/README.md) | 54 | 84,343 | IPOs, earnings, mergers, stock-pick lists — dated and perishable. |
| [indicators](indicators/README.md) | 53 | 50,622 | VWAP, MACD, RSI, moving averages, oscillators. |
| [crypto](crypto/README.md) | 44 | 32,517 | Bitcoin, altcoins, exchanges, blockchain. |
| [candlesticks](candlesticks/README.md) | 36 | 38,460 | Individual candle shapes: doji, hammer, engulfing, shooting star. |
| [order-types](order-types/README.md) | 35 | 48,244 | Limit, stop, iceberg, IOC, ISO, market-on-open. |
| [market-concepts](market-concepts/README.md) | 34 | 46,306 | Market behaviour and plumbing: seasonality, price discovery, PFOF, market make |
| [chart-patterns](chart-patterns/README.md) | 27 | 25,139 | Multi-candle formations: wedges, channels, double tops, Elliott/Wolfe waves, p |
| [getting-started](getting-started/README.md) | 22 | 31,522 | Capital requirements, small accounts, going full time, prop firms. |
| [market-notes](market-notes/README.md) | 22 | 24,195 | Weekly market overviews and watch lists. |
| [short-selling](short-selling/README.md) | 22 | 28,463 | Shorting mechanics, borrow, short interest, squeezes. |
| [community-company](community-company/README.md) | 19 | 16,413 | Student profiles, testimonials, site and company pages. |
| [off-topic](off-topic/README.md) | 13 | 20,544 | Lifestyle and general interest — kept separate so a trading search does not su |
| [quotes-answers](quotes-answers/README.md) | 12 | 3,137 | Quote pages and Q&A stubs. |
| [books-education](books-education/README.md) | 5 | 3,480 | Book lists and course material. |
