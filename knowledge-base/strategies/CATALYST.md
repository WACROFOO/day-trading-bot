# The desk's catalyst grade — rules and where each one comes from

**What this is.** The two-line catalyst read on the desk card and in
`scripts/catalyst_score.py`: a grade (STRONG / MODERATE / WEAK), its one-line
reason, the type, the age, the headline in two lines, and flags. Code:
`src/momentum_platform/catalyst.py` (`card_read`). Every grade carries the id
of the rule that produced it; a test fails if the code returns an id this file
does not list.

**What it is not.** The grade is display. The gate that counts is FILTERS.md
gate 3 — a catalyst *dated today*, or a live theme — and in this paper exercise
it flags rather than kills (amendment A2, `docs/preregistration.md` §5) while
feeding the Five Pillars count. A STRONG grade never sizes, never arms, never
outranks the chart.

**The boundary of the evidence.** The corpus says a catalyst should be real,
fresh and economically meaningful, and that the catalyst outranks the chart.
It does not give a numeric strength scale. Where the three grades split is this
desk's choice, labelled **Approximation**; the rules each split rests on are
quoted with their source.

| id | rule | origin |
|---|---|---|
| C0 | No headline feed on the desk → **UNKNOWN**, never WEAK: the desk cannot say there was no news when it never looked | desk rule, fails closed (cascade gate 3, amendment A2) — Approximation of the six-state vocabulary |
| C1 | Only the company's own headlines count: market roundups, reaction pieces ("why is X soaring") and stories tagged from another company are skipped | Approximation — desk audits of 2026-09-08, 2026-09-17 and 2026-09-21 (`src/momentum_platform/catalyst.py` comments) |
| C2 | "Dated today" = published after 16:00 ET of the previous **trading** day; weekend and holiday news belongs to the next session | FILTERS.md gate 3 ("none dated today"); the overnight extension is an Approximation. Until 2026-10-08 the cutoff was the previous calendar day |
| C3 | **STRONG** — the company's own headline, dated today, in the hard family: FDA or clinical results, earnings or guidance, a contract or order, an acquisition by the company, a patent, an uplist | Confirmed course: the catalyst taxonomy and the question "does the event have quantifiable economic value?" (`CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/day-trading-basics-preview-mastery.md`, `CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/strategy-playbook.md` §12). Ross: *"what's more important a strong Catalyst or a strong chart without a doubt catalyst is number one"* — `YZ5nvP7DnQQ` [00:25:38]. Which words count as "hard" is an Approximation |
| C4 | **MODERATE** — dated today but attention without stated value: a partnership, agreement, MOU, collaboration or analyst action | Confirmed course caution: "Partnerships must be economically meaningful; promotional wording can exaggerate ordinary vendor relationships" (`CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/day-trading-basics-preview-mastery.md`). The grade is an Approximation |
| C5 | **WEAK** — a press release without substance (appointment, conference, "announces" with nothing behind it), a listing notice, or no company news since the cutoff (then the news pillar fails) | Ross on promoted moves: *"that's not really a strong Catalyst I'd prefer a catalyst that's based on some type of news event"* — `iBNcF_lPBIg` [00:15:48]. The playbook: do not read a headline as positive only because it says "partnership", "agreement" or "AI" (`CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/strategy-playbook.md`). FILTERS.md gate 3 for the no-news case |
| C6 | An offering, placement, ATM, warrant or PIPE headline is **supply, not a catalyst**: WEAK when it is the only news, a red flag beside a real catalyst (the grade then comes from the catalyst) | Confirmed course: "A secondary offering is usually bearish" (`CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/day-trading-basics-preview-mastery.md`); FILTERS.md "Capital structure". The flag-beside rule is an Approximation, written after LPCN 2026-10-07 read DILUTIVE at 07:26 and STRONG at 07:54 on the newest headline alone |
| C7 | A headline making the company a **buyout target** grades WEAK and is flagged: the price pins near the deal | FILTERS.md gate 8: *"the value becomes fixed at the buyout price and volatility disappears"* |
| C8 | **MODERATE** — yesterday's hard headline (before the cutoff) with nothing new today: day-2 interest | FILTERS.md, the book's six components, #3: greed, *"one-day-old FOMO"*. The grade is an Approximation |
| C9 | An SEC filing with nothing readable behind its form and item codes (a 6-K, an 8-K "other events" with no body sentence) is an **unread filing**: WEAK, and it does not count as news | Approximation, fails closed. Until 2026-10-08 a bare `SEC 6-K · 6-K` graded WEAK and passed the news pillar |
| C10 | A shelf on file (S-3, S-3ASR, S-1, F-1, F-3) is flagged: the company can issue at any time. "Filings not checked" is said, never implied clean | FILTERS.md "Capital structure — no screener sees these" (live ATM or shelf vs market cap); Confirmed course: "A shelf is a risk flag, not proof that an offering will occur immediately" |
| C11 | A takedown (424B1–7, FWP) filed in the last 30 days is a red flag: shares are being sold now; older is history | the 30-day line is an Approximation. Until 2026-10-08 the CLI read AVOID on any 424B inside its 90-day window, however old |
| C12 | A foreign private issuer (6-K, 20-F, 40-F, F-1, F-3 on file) is flagged as the dilution blind spot: no S-3/424B tripwire, check EDGAR by hand | CLAUDE.md rule 7 |
| C13 | The reverse-split test is reported as run, failed (the gap is the split) or not run | CLAUDE.md rule 6; FILTERS.md gate 5 |

**The two lines.** Line 1: the grade and its reason. Line 2–3: the headline,
clamped to two lines (the full text on hover, the SEC link when there is one).
Then type · age · source and the flags. Age reads "today 07:02 · pre-market",
"after yesterday's close · 17:00", "yesterday 10:00" or "N days old".

**Limits.** The desk reads headlines, not bodies: a hard word in a promotional
headline grades hard, and a dry headline over a large contract may grade soft.
The headline is always on the card so a human overrules the grade in one read.
EDGAR's recent-filings list covers about a year; an older shelf is not seen.
