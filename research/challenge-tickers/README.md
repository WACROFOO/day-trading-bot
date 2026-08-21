# Tickers he traded, by session — the $2,000 challenge

```
Reproduce: python3 scripts/challenge_tickers.py \
    --meta research/momentum-replication/data/july_meta.json \
    --vtt knowledge-base/recaps --since 20260601 --min-hits 3
SOURCES · his daily recap videos. Two spans, two very different
       evidence levels — do not read them as one table:
       2026-06-01 .. 2026-07-29  captions IN THE CORPUS (68 videos) -> extracted
       2026-07-30 .. 2026-08-21  titles + dates fetched 2026-08-21; CAPTIONS NOT
                                 OBTAINED (YouTube bot-gates this datacenter IP)
VALIDATION · every extracted symbol is checked against the REAL tape for
       that session (Yahoo daily bars). Auto-captions garble spelled-out
       tickers — one recap renders INLF as INFL, INLX and INFS in a
       single paragraph (knowledge-base/recaps/README.md) — so extraction
       alone is noise. A row survives only if the symbol resolves AND
       moved that day.
       CONFIRMED  >= 20% intraday range that session
       WEAK       8-20% range — mentioned, not the star
       (NO-MOVE and NO-DATA candidates are dropped, not shown)
LIMIT · "he said it on the recap" is not "he traded it". The recaps name
       the day's movers he watched AND the ones he traded; this table is
       the union. Position, entry and P&L are NOT extracted.
```

## Funnel

68 recap videos (June 1 – July 29) → candidates mentioned 3+ times →
tape check per session → **73 CONFIRMED session-ticker pairs across 31
sessions, 59 distinct symbols**, plus 13 WEAK. Full rows, WEAK included,
in `challenge-tickers.csv` (date, ticker, class, move, mentions, video ids).

Most recurrent names: **ICCM** and **BIYA** (3 sessions each), then
TGHL, NXTS, PLSM, JEM (2 each).

## The sessions — CONFIRMED only, move = intraday range / close change

| session | tickers (validated on that day's tape) |
|---|---|
| 2026-06-01 Mon | **TGHL** r91% / +288% |
| 2026-06-04 Thu | **STI** r102% / +351% |
| 2026-06-08 Mon | **NPT** r834% / +284% |
| 2026-06-09 Tue | **CCTG** r276% / +272% |
| 2026-06-10 Wed | **VSME** r173% / +149% · **DSY** r211% / +291% · **CIIT** r204% / +34% · **KIDZ** r26% / -26% · **PAVS** r108% / -51% |
| 2026-06-11 Thu | **EDHL** r199% / +71% · **FGL** r20% / +3% |
| 2026-06-15 Mon | **CUPR** r111% / +112% · **JRSH** r52% / +8% |
| 2026-06-16 Tue | **TDIC** r47% / +40% |
| 2026-06-17 Wed | **EHGO** r186% / +119% · **ICCM** r165% / +200% · **UTSI** r48% / -1% · **CLWT** r74% / +31% |
| 2026-06-22 Mon | **ICCM** r34% / +10% · **NXTS** r116% / +156% |
| 2026-06-23 Tue | **NXTS** r27% / -55% · **ICCM** r27% / +3% |
| 2026-06-24 Wed | **FRTT** r250% / -28% · **PLSM** r110% / +93% |
| 2026-06-25 Thu | **FCUV** r50% / +8% |
| 2026-06-26 Fri | **ZDAI** r57% / +5% · **SHPH** r64% / +6% |
| 2026-06-29 Mon | **UPC** r71% / +311% |
| 2026-06-30 Tue | **SVRE** r192% / -3% · **JEM** r64% / +268% · **CELZ** r245% / +79% |
| 2026-07-06 Mon | **GMEX** r46% / -18% · **LHSW** r57% / +278% |
| 2026-07-07 Tue | **CLRO** r103% / +98% · **TDTH** r33% / +41% |
| 2026-07-10 Fri | **GMM** r79% / +147% |
| 2026-07-13 Mon | **PLSM** r53% / -6% |
| 2026-07-14 Tue | **NXTC** r72% / +202% |
| 2026-07-15 Wed | **ERNA** r62% / +11% |
| 2026-07-16 Thu | **TGHL** r39% / +87% · **VEEE** r34% / +36% · **IQST** r22% / +38% |
| 2026-07-17 Fri | **SLND** r33% / +67% · **CJMB** r22% / +42% · **BIYA** r22% / +36% |
| 2026-07-20 Mon | **BIYA** r240% / -15% · **ZYBT** r573% / +1048% |
| 2026-07-22 Wed | **ZYBT** r75% / -52% · **CPHI** r77% / -79% · **ZCMD** r462% / +192% |
| 2026-07-23 Thu | **ZCMD** r224% / -60% |
| 2026-07-24 Fri | **VIVK** r55% / +37% · **EXYN** r29% / -14% · **AMIX** r29% / -17% · **CJMB** r77% / +9% · **JEM** r39% / +34% · **RADX** r44% / -17% · **ADVB** r50% / +13% · **LVWR** r44% / +90% · **AKAN** r97% / -4% · **WLDS** r79% / +58% · **OMH** r366% / +19% · **MSS** r85% / -28% |
| 2026-07-27 Mon | **EDBL** r207% / -7% · **LGHL** r117% / +17% |
| 2026-07-28 Tue | **DFNS** r83% / +83% · **INLF** r98% / +62% · **LGHL** r96% / +1% · **BIYA** r69% / +54% |
| 2026-07-29 Wed | **NCRA** r62% / +118% · **DFNS** r100% / +109% · **STFS** r56% / +32% · **AMIX** r84% / +66% |

## 2026-07-30 → 2026-08-21 — the gap, stated plainly

His 12 most recent videos, dates and titles fetched today. **Captions
could not be retrieved from this machine**: YouTube answers metadata but
bot-gates the caption endpoint for this datacenter IP (`Sign in to
confirm you're not a bot`, then HTTP 429). Titles alone name no tickers
and the descriptions are boilerplate, so nothing is extracted for this
span — rather than guessing from the day's movers, which would be
inference dressed as evidence.

| upload | title | video id |
|---|---|---|
| 2026-08-21 Fri | Biotech Stock Up 114% 🤩 | `6N5OdC3zl0c` |
| 2026-08-20 Thu | +$19,323...My Account is up 31% in 2 Trades TODAY... | `EvaLoKjzKqY` |
| 2026-08-19 Wed | BIGGEST RED DAY... | `Q6oWxbuvoqA` |
| 2026-08-18 Tue | Five Stocks Are Up More Than 100% Today... | `qNTugIPRrP8` |
| 2026-08-17 Mon | I Was Red -$12k Before My Big Winner... | `OzLePbEE5nE` |
| 2026-08-17 Mon | Day Trading A Stock Up 260% in 1 Day... | `7D3k0Ui_cPY` |
| 2026-08-16 Sun | 4 Stocks On Watch for Monday Morning! | `yHrlQ5_Sc6c` |
| 2026-08-14 Fri | MAX LOSS RED DAY (mistakes were made) | `kIZS4bU2Jpo` |
| 2026-08-14 Fri | Red Day Recap | `2BMJ5DjTeUo` |
| 2026-08-13 Thu | Penny Stock Goes Up 1,753% in 10 Minutes | `Rd8nj1NCBS4` |
| 2026-08-12 Wed | Penny Stocks Are Back... | `9x5ww56Ls7U` |
| 2026-08-02 Sun | These Are The TWO Stocks I'm Watching for Monday... | `50iICFBL5kA` |

**To close the gap from your own machine** (a home IP is not bot-gated):

```bash
pip install yt-dlp
mkdir -p aug_recaps && cd aug_recaps
yt-dlp --skip-download --write-auto-subs --sub-langs en --sub-format vtt \
  -o "%(id)s.%(ext)s" \
  https://www.youtube.com/@DaytradeWarrior/videos --playlist-end 15
```

then, back in the repo:

```bash
python3 scripts/challenge_tickers.py --meta <aug_meta.json> --vtt aug_recaps \
    --since 20260730 --min-hits 3
```

`aug_meta.json` (ids, dates, titles for those 12) is already fetched — it
is the metadata behind the table above and ships in this folder.

## What this could not check

- **Traded vs merely discussed** — the recaps mix both; only a P&L
  screenshot or his stated entries separate them, and neither is parsed.
- **Size, entry, exit, result** — not extracted. The existing
  calibration report does entry-level comparison for July
  (`research/momentum-replication/reports/2026-07-july-calibration.md`).
- **Symbols that never resolved** — a garbled ticker with no Yahoo match
  is dropped silently; a real but delisted symbol would drop the same way.
- **The August span** — see above. No captions, no rows.

Paper only. This is a labelled list of what he talked about after the
close, useful as a calibration set — not a watchlist and not advice.

---

# Tous les tickers du corpus, datés par leur megaday

```
Reproduire : python3 scripts/corpus_tickers.py --min-files 2 --min-range 30 \
                 --out research/challenge-tickers/corpus-megadays.csv
SOURCE · les QUATRE registres, pas seulement les recaps :
         transcripts (258) + summaries (260) + streams (290) + recaps (69)
         = 873 fichiers, 1 711 tokens majuscules, 665 candidats retenus
         (cités dans >= 2 fichiers distincts).
DATE · le megaday n'est PAS la date de la vidéo. C'est la séance où le
       titre a fait son plus grand range intraday, mesurée sur les barres
       journalières. Un token inventé par les sous-titres n'a pas de
       megaday et disparaît : c'est le filtre.
RÉSULTAT · 250 tickers avec un megaday >= 30 % de range.
```

| année du megaday | tickers |
|---|---|
| 2021 | 12 |
| 2022 | 28 |
| 2023 | 26 |
| 2024 | 60 |
| 2025 | 61 |
| 2026 | 63 |

Registres où ils sont cités : streams 123, transcripts 120, summaries 104, recaps 90.

## Les 40 megadays les plus récents (depuis juin 2026)

| megaday | ticker | range | var. clôture | volume | fichiers |
|---|---|---|---|---|---|
| 2026-06-01 | **NXTC** | 146% | -45.5% | 922,500 | 2 |
| 2026-06-02 | **HKIT** | 195% | -90.6% | 964,892 | 2 |
| 2026-06-04 | **VERU** | 247% | 88.0% | 92,865,600 | 2 |
| 2026-06-08 | **TDIC** | 260% | 123.7% | 22,877,648 | 5 |
| 2026-06-09 | **CCTG** | 276% | 271.6% | 119,339,800 | 4 |
| 2026-06-09 | **AZI** | 317% | 63.7% | 190,648,400 | 2 |
| 2026-06-10 | **DSY** | 211% | 291.3% | 113,587,700 | 6 |
| 2026-06-12 | **CUPR** | 156% | 64.7% | 83,262,200 | 3 |
| 2026-06-15 | **PAVS** | 206% | -8.7% | 6,713,637 | 3 |
| 2026-06-16 | **GDC** | 359% | -73.3% | 3,201,829 | 5 |
| 2026-06-17 | **ICCM** | 165% | 200.5% | 152,922,500 | 4 |
| 2026-06-17 | **CLWT** | 74% | 30.8% | 78,755,100 | 2 |
| 2026-06-24 | **PLSM** | 110% | 93.3% | 58,325,600 | 7 |
| 2026-06-24 | **FRTT** | 250% | -28.2% | 78,866,300 | 4 |
| 2026-06-24 | **RAM** | 52% | % | 14,248,800 | 3 |
| 2026-06-25 | **ROC** | 38% | 14.8% | 202,000 | 3 |
| 2026-06-30 | **CELZ** | 244% | 79.0% | 188,686,100 | 3 |
| 2026-06-30 | **SVRE** | 192% | -2.9% | 27,354,900 | 2 |
| 2026-06-30 | **ADTX** | 200% | 200.0% | 204,136,200 | 2 |
| 2026-07-01 | **JEM** | 300% | -19.1% | 6,465,533 | 3 |
| 2026-07-02 | **CLRO** | 208% | 101.2% | 87,174,400 | 7 |
| 2026-07-14 | **LGHL** | 176% | 10.7% | 33,435,900 | 3 |
| 2026-07-20 | **BIYA** | 240% | -15.2% | 75,620,900 | 6 |
| 2026-07-21 | **OMH** | 394% | 222.4% | 304,781,400 | 6 |
| 2026-07-21 | **VIVK** | 287% | 49.1% | 141,350,600 | 2 |
| 2026-07-22 | **LABT** | 128% | 83.3% | 79,569,700 | 2 |
| 2026-07-22 | **ADVB** | 132% | 73.0% | 29,586,600 | 2 |
| 2026-07-24 | **SXTC** | 400% | -80.8% | 324,050,300 | 2 |
| 2026-07-27 | **SK** | 34% | -14.9% | 758,300 | 3 |
| 2026-08-03 | **GV** | 85% | -20.0% | 204,700 | 3 |
| 2026-08-04 | **AMIX** | 371% | 434.2% | 120,033,100 | 3 |
| 2026-08-05 | **ZYBT** | 240% | 84.4% | 71,604,500 | 3 |
| 2026-08-21 | **SUGP** | 279% | -42.3% | 39,657,361 | 3 |

Liste complète : `corpus-megadays.csv` — ticker, megaday, range %, variation
de clôture, volume, nombre de fichiers du corpus qui le citent, et dans
quels registres.

## Ce que ça ne dit pas

- **« cité dans le corpus » n'est pas « il l'a tradé ».** Les registres
  mélangent trades pris, noms de watch-list et exemples pédagogiques. La
  colonne `registers` dit de quel type de mention il s'agit : `recaps` =
  il en a parlé après la séance, `streams` = décision en direct,
  `transcripts`/`summaries` = matériel d'enseignement.
- **Le megaday peut être postérieur à la vidéo.** Un titre cité en 2022
  peut avoir explosé en 2025 ; la date donnée est celle du plus gros
  range, pas celle de la mention.
- **Les prints aberrants sont filtrés, pas corrigés.** Les barres dont le
  plus bas est sous 25 % de la clôture sont rejetées : sur un reverse
  split Yahoo sert des prints comme CRKN 2026-08-13 bas $0,0002 /
  clôture $0,0003, soit un « range » de 49 900 % qui n'a jamais eu lieu
  (règle 6 du CLAUDE.md). Le range est aussi plafonné à 400 %.
- **Aucune vérification du flottant, du catalyseur ou des halts** ici.

Paper only.
