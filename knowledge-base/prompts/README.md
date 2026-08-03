# prompts/

Ready-to-paste prompts for agents that work outside this repo.

| File | For | Does what |
|---|---|---|
| `tradingview-setup-agent.md` | Claude Chrome extension, on TradingView | Connects paper trading, builds the 2x2 chart layout with indicators and extended hours, creates the watchlist, saves the three screeners |

Conventions that make these work on a browser agent: explicit ordered tasks, a
stated fallback wherever a feature may be plan-gated, per-task reporting, and
a final summary that asks what could NOT be done. Without the fallbacks an
agent will quietly improvise and you will not know which of your filters are
real.
