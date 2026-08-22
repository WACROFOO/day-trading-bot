# Audit barre d'entrée — ambiguïté trigger/stop intra-barre

- 162 fills propres (artefacts stop<0,05% exclus). Tuning only, cutoff 2025-09-10.
- Ambigu = stop touché sur la barre d'entrée: le low a pu précéder OU suivre le trigger, ordre inconnaissable en OHLC 1-min.

- **Ambigus: 26%** (42/162) — coïncide avec les 25% mesurés sur tape réelle en août.
- +1R atteint sur la barre d'entrée: 31% des fills (propre, stop non touché: 24%).

## Espérance du ladder (moitié à 1R, reste à 2R/BE) sous 3 hypothèses

| population | naïf | ambigus exclus | ambigus = -1R (pire cas) |
|---|---|---|---|
| tous (n=162) | +0.47R | +0.48R | +0.10R |
| NHD (n=62, 27% ambigus) | +0.71R | +0.64R | +0.19R |
| non-NHD (n=100, 25% ambigus) | +0.32R | +0.39R | +0.04R |

## Lecture

- L'ambiguïté coûte ~0,5R en pire cas sur NHD (+0,71 → +0,19) mais ne fait PAS passer l'espérance sous zéro.
- Elle ne suffit donc pas, seule, à expliquer des backtests négatifs — reste les gates VWAP/MACD (population) et le slippage/spread (exécution).
- 26% de fills structurellement indécidables en 1-min: toute mesure OHLC de cette stratégie porte cette incertitude en bande de base.
