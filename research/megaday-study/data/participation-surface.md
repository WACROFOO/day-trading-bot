# Surface participation — quelle SORTIE domine à travers les largeurs

- Entrée: 1er repli NHD du jour. n = 37 jours. Ambigus en pire cas.
- Compte €2000, risque 2%, commission €1/ordre.
- `clock_1130` = RÉFÉRENCE calibrée sur l'échantillon (HOD médian 11:34), pas une candidate.

## Espérance en R

| sortie \ stop | 1× | 2× | 3× | (n) |
## Slippage 0.25% — R moyen (€ moyen)

| sortie \ stop | 1× | 2× | 3× | n |
|---|---|---|---|---|
| trail_dip | +0.19R (+5.7€) | +0.50R (+17.9€) | +0.37R (+12.8€) | 37 |
| vwap | +0.22R (+6.6€) | +0.37R (+12.8€) | +0.40R (+14.1€) | 37 |
| lower_highs | +0.19R (+5.7€) | +0.50R (+17.9€) | +0.37R (+12.8€) | 37 |
| clock_1130 *(réf.)* | +0.12R (+2.9€) | +0.13R (+3.4€) | -0.06R (-4.4€) | 37 |

## Slippage 0.50% — R moyen (€ moyen)

| sortie \ stop | 1× | 2× | 3× | n |
|---|---|---|---|---|
| trail_dip | +0.04R (-0.3€) | +0.42R (+14.8€) | +0.32R (+10.7€) | 37 |
| vwap | +0.06R (+0.6€) | +0.29R (+9.8€) | +0.35R (+12.1€) | 37 |
| lower_highs | +0.04R (-0.3€) | +0.42R (+14.8€) | +0.32R (+10.7€) | 37 |
| clock_1130 *(réf.)* | -0.03R (-3.1€) | +0.06R (+0.4€) | -0.11R (-6.4€) | 37 |

## Audit des raisons de sortie (2x, slip 0,25%)

| sortie | stop | regle propre | fin de journee |
|---|---|---|---|
| trail_dip | 29 | 0 | 8 |
| vwap | 18 | 16 | 3 |
| lower_highs | 29 | 0 | 8 |
| clock_1130 | 18 | 19 | 0 |

`trail_dip` et `lower_highs` degenere(nt): leur regle ne declenche JAMAIS — ces colonnes mesurent en fait
« hold = stop ou cloture ». C'est donc la participation maximale qui gagne (+0,42R a 2x), pas une sortie
de structure fine. `vwap` declenche 16 fois et fait moins bien: sortir sur structure COUTE vs tenir.
`clock_1130` (reference) est la pire ligne: l'horloge seule sous-performe meme le hold naif.
