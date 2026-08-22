# NHD-MFE — le split décisif

- Tuning split uniquement (cutoff 2025-09-10, holdout intact). 176 pullbacks shape sur jours propres.
- Entrée = break de la dernière barre rouge (§4), stop = bas du dip, MFE jusqu'au stop ou EOD.
- NHD = l'impulsion a fait un nouveau plus haut du JOUR (pré-market inclus).

- **Impulsion NHD (nouveau plus haut du jour)**: 62 fills (6% sans fill) — MFE en R: médiane 2.04 (p25 1.28, p75 6.72), moyenne 8.84
  - P(MFE ≥ 1R): 81% | P(MFE ≥ 2R): 50% | P(MFE ≥ 3R): 45% | P(MFE < 0,25R): 8%

- **Impulsion SANS nouveau plus haut du jour**: 102 fills (7% sans fill) — MFE en R: médiane 1.35 (p25 0.67, p75 6.46), moyenne 14.65
  - P(MFE ≥ 1R): 61% | P(MFE ≥ 2R): 43% | P(MFE ≥ 3R): 33% | P(MFE < 0,25R): 12%

- Contrôle: parmi les fills NHD, 3% entrent après le HOD vs 47% des non-NHD.
- MFE médian NHD vs non-NHD: 2.04R vs 1.35R

## Artefacts de stop à 1 tick

- 2 lignes avec stop < 0,05% du prix (multiples de R irréalistes):
  - RADX 2024-12-06: MFE 291R, stop 0.034%
  - HIT 2025-05-14: MFE 375R, stop 0.011%
- Moyennes nettoyées: NHD 8.84R vs non-NHD 8.28R

## Temps d'atteinte de +1R / +2R (en barres de 1 min depuis l'entrée)

- **NHD** (n=62): +1R en médiane 1 barres (p25 0, p75 1, p90 4) | +2R en médiane 2 barres (p75 6)
  - Parmi ceux qui atteignent +1R: 14% mettent >2 barres (amputés par un bailout à 2 barres); atteints en ≤2 barres: 86%
- **non-NHD** (n=100): +1R en médiane 0 barres (p25 0, p75 1, p90 3) | +2R en médiane 2 barres (p75 6)
  - Parmi ceux qui atteignent +1R: 17% mettent >2 barres (amputés par un bailout à 2 barres); atteints en ≤2 barres: 83%
- **tous** (n=162): +1R en médiane 1 barres (p25 0, p75 1, p90 4) | +2R en médiane 2 barres (p75 6)
  - Parmi ceux qui atteignent +1R: 15% mettent >2 barres (amputés par un bailout à 2 barres); atteints en ≤2 barres: 85%

## Distance du stop

- Stop en % du prix: médiane 3.03% (p10 1.24%, p90 8.09%)
- Fraction des setups avec stop > 3% (cap maxStopPct): 51%

Si les deux distributions se ressemblent, l'hypothèse NHD tombe. Sinon la stratégie tient en une phrase:
acheter le repli qui suit un nouveau plus haut du jour, pendant la construction, sortir avant la purge.
