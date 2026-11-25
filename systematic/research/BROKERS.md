# Broker choice: PEA and CTO (November 2026)

A summary of the two research notes in
[research_notes/PEA broker comparison/](research_notes/PEA%20broker%20comparison/).
Fees come from each broker's official schedule where possible; the notes flag
what could not be checked on an official page. Costs below use illustrative
order sizes (a €3,000 lump sum, then €500 a month into one PEA MSCI World ETF).

## PEA: Bourse Direct, with Trade Republic as a close second

| Rank | Broker | €3,000 order | Each €500 monthly order | Free automatic monthly plan in the PEA | Annual fees | Protection |
|---|---|---|---|---|---|---|
| 1 | **Bourse Direct** (FR) | €3.80, or €0 through the plan | **€0** (plan) | **Yes: WPEA, DCAM, CW8 named by ISIN**, monthly or quarterly, no minimum | None | FGDR (France), €70k |
| 2 | Trade Republic (DE, French branch) | €1 | €0 (plan) | Yes (official page); plan details not confirmed | None | German scheme; no phone support |
| 3 | BoursoBank (FR) | €15 for WPEA; DCAM likely €0 (unconfirmed) | €1.99 for WPEA | Not suitable (its plan doesn't buy WPEA/DCAM directly) | None | FGDR |
| 4 | XTB (PL) | €0 | €0, but manual | No | None | Polish scheme; no transfers in |
| 5 | Fortuneo (FR) | €10.50 | €0 if it is the month's first order (manual) | No | €85 closure fee | FGDR |
| 6 | Saxo (DK) | €0 until 31 Dec 2026, then €2.40 | €0, then €2 | Not confirmed in the PEA | — | Danish scheme |
| 7 | IBKR (IE) | ~€1.50 + exchange fee | ~€1.25 + exchange fee | **No plan, no fractional shares** | None | Irish scheme (90% up to €20k) |
| — | Traditional banks (SG, BNP) | €10–13.50 | €2.50 | — | **0.3–0.4% a year custody**, the main cost over time | FGDR |

**Recommendation: Bourse Direct.** It is the only French broker whose own
schedule names WPEA and DCAM as free in an automatic monthly plan. That makes
stage 1 fully automatic: the €500 is invested on the 5th of every month with no
action from you. It also has no custody fees, cheap transfers out (€15 per
line, capped at €150 by law), France's FGDR protection, and it issues the French
tax form (IFU).

Trade Republic is equally cheap. It ranks second on lower investor protection,
no phone support, and plan details its own pages don't confirm.

**Caveat:** Bourse Direct's plan appears to buy whole units only. At a unit
price of a few euros that leaves a few euros in cash each month, which the next
month's purchase uses.

**PEA fee caps (law, since 2020):**
- opening: €10
- custody: 0.4% a year + €5 per line
- online orders: 0.5%
- transfer out: €15 per line, €150 in total

## IBKR: keep it, for the CTO from stage 2, not for the PEA

IBKR has offered a PEA since late 2024, but it is a weak choice for the
monthly core purchase. There is no automatic plan and no fractional shares,
and a Finary thread from September–October 2026 reports a PEA transfer out
blocked because the IBKR PEA has no IBAN.

**As the CTO (stage 2, from €10k), IBKR is a good fit:**
- the widest range of UCITS ETFs on a single fee schedule
- no custody or inactivity fees
- cheap currency conversion
- fractional shares and recurring purchases on the CTO
- commission-free recurring purchases of iShares ETFs since June 2026
  (eligibility for French residents still to confirm)
- a mature API for stage 3 automation

**What you must handle with IBKR:**
1. **Form 3916 every year, starting now.** Any IBKR account must be declared
   every year, **even if unused**: €1,500 per account per year if missed, with
   a 10-year reassessment window. If the account was open in earlier years and
   not declared, regularise those years.
2. **No French tax form (IFU) for the CTO.** You compute gains yourself (form
   2074) from IBKR's statements.
   - *Upside:* losses from past trading in that account, if declared, can be
     carried forward for 10 years against future gains.
3. **Avoid the monthly prepayment forms.** Use accumulating ETFs and keep cash
   under €10k, so there are no dividends or interest and therefore no monthly
   2778 filings.
4. **Account settings:** switch to *Tiered* pricing (the €3 *Fixed* minimum is
   expensive on small orders), buy euro-denominated listings, and keep a cash
   (non-margin) account.
5. **Protection is lower than at a French broker:** the Irish scheme pays 90%
   of losses up to €20k, against €70k under FGDR, plus IBKR's private excess
   insurance. IBKR itself is large and well capitalised: 5.6M accounts and
   about $965bn of client equity in Q3 2026.

This is not tax advice: confirm the 3916 and 2074 points with an accountant.
