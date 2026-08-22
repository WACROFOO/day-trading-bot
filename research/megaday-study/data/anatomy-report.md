# Megaday anatomy v2 — tuning set (description only)

- Full day 04:00-20:00 ET, **pre-market inclus**. Tuning split only (cutoff 2025-09-10, holdout untouched).
- 50 jours propres (8 artefacts de split exclus, 58 jours couverts / 135 tuning).

## Pre-market: la journée ne commence pas à 09:30

- Part du range journalier formée AVANT 09:30: médiane 0.18 (p25 0.04, p75 0.37)
- HOD atteint en pré-market: 12% des jours
- Heure du HOD (journée complète): médiane 11:34 ET (p25 10:20, p75 14:32)
- 50% du move (depuis 04:00) formé à: médiane 10:28 | 90% à 11:30

## Les 5 premières minutes de la session régulière

- Part du range JOURNALIER COMPLET formée 09:30-09:35: médiane 0.06
- Part du move encore disponible à 09:35: médiane 0.97 (p25 0.79, p75 1.00)
- NB: avec le pré-market inclus, ce n'est plus une tautologie du timing du HOD — le dénominateur est la journée entière.

## Dips — le dip typique vs le pire dip

- **Tous les dips poolés** (déf. lâche ≥15% du running range): n=342, médiane 0.39, p75 0.77, p90 1.32 du running range
- Fraction des dips qui passent SOUS l'open (profondeur >1): 14%
- Pire dip du jour (médiane des max, v1): 1.22 — c'est un effet de sélection, pas le dip typique
- Nombre de dips/jour (déf. lâche): médiane 7

## Pullbacks au sens de la shape (PARAMETERS.md)

- Pullbacks shape-valids (impulsion ≥ max(5%, 2×ATR), efficience ≥0.6, volume ≥ médiane, puis 1-4 barres rouges, retrace ≤50%): total 170, médiane 3/jour (p25 1, p75 5)
- Jours avec au moins un pullback shape-valide: 92%
- Profondeur des dips shape (en % de la jambe d'impulsion): médiane 39%, p75 45%, p90 49%
- Dips shape suivis d'un new high: 89%
- Premier pullback shape: médiane à 10:00 ET (n=46), suivi d'un new high dans 91% des cas

## Giveback et amplitude (journée complète)

- Giveback HOD→close, % du move: médiane 71% (p25 43%, p75 102%)
- Move open(04:00)→HOD: médiane 173% (p25 104%, p75 256%)

## Caveats

- 74/135 tuning events (surtout 2022-2024) sans candles 1m: sous-ensemble couvert biaisé vers 2025.
- Shape = implémentation opérationnelle de PARAMETERS.md §4/§13 sur barres 1-min; un pullback 10-secondes est invisible à cette résolution (§13).
- Holdout (>= 2025-09-10) non touché.
