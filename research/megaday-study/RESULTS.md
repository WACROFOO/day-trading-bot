# Étude megadays — résultat, et pourquoi elle se ferme

```
PLAN · PLAN.md, écrit avant toute mesure : holdout gelé d'abord, anatomie,
     taux de base, segmentation, 3-5 hypothèses, une seule validation.
     Le plan a été suivi. Le protocole de lecture du holdout a été figé
     AVANT de le lancer (data/holdout-protocol.md).
DONNÉES · 250+ megadays en barres 1 min, 04:00-20:00 ET. Tuning = 135
     événements avant 2025-09-10 (58 jours couverts, 50 propres après
     retrait des artefacts de split). Holdout = 80 jours gelés,
     2025-09-10 → 2026-08-21, ouverts une fois.
ARTEFACTS · tout est dans data/ : anatomie, dips, MFE, audit de la barre
     d'entrée, surfaces, protocole, et les 31 trades du holdout.
VERDICT · en bas, comme il se doit.
PAPER ONLY.
```

## Entonnoir

250 megadays → 135 en tuning → 58 avec barres 1 min → 50 propres →
342 dips au sens large → **170 pullbacks conformes à la shape** →
164 fills → 62 après le filtre NHD. Puis 80 jours gelés → **31 fills**.

Ce qui a été jeté et pourquoi : 74/135 événements tuning sans barres 1 min
(surtout 2022-2024, sous-ensemble biaisé vers 2025) ; 8 jours d'artefacts
de reverse split ; 2 fills à stop d'un tick (HIT MFE 375R sur un stop de
0,011 % du prix, RADX 291R sur 0,034 %) — irréalistes, retirés, signalés.

## 1. Anatomie — la journée ne ressemble pas à ce que la stratégie suppose

| mesure | valeur |
|---|---|
| range formé avant 09:30 | médiane **18 %** (p75 37 %) |
| HOD atteint en pré-market | **12 %** des jours |
| heure du HOD | médiane **11:34 ET** (p25 10:20, p75 14:32) |
| 50 % / 90 % du move formé à | **10:28** / **11:30** |
| move open(04:00) → HOD | médiane **173 %** |
| rendu entre HOD et clôture | médiane **71 %** (p75 102 %) |
| pullbacks conformes par jour | médiane **3** (p25 1, p75 5), 92 % des jours ≥ 1 |
| profondeur d'un dip conforme | médiane **39 %** de la jambe (p90 49 %) |
| dips conformes suivis d'un new high | **89 %** |

Deux conséquences immédiates :

- **La borne de retracement à 50 % ne filtre rien** : la médiane est à
  39 %, le p90 à 49 %. Elle ne mord que sur les queues. Des semaines de
  réglage ont porté sur un gate inerte.
- **21 % des jours, le premier pullback conforme arrive APRÈS le sommet
  du jour** (11 jours sur 52 ; quand il arrive avant, la marge médiane
  est de 206 min). Acheter « le premier pullback » revient donc, une fois
  sur cinq, à acheter le fade par construction.

## 2. Le filtre NHD — acheter le repli qui suit un nouveau plus haut du jour

| | NHD (62 fills) | non-NHD (102) |
|---|---|---|
| MFE médian | **2,04R** | 1,35R |
| P(MFE ≥ 1R) | 81 % | 61 % |
| P(MFE ≥ 3R) | 45 % | 33 % |
| entrées après le HOD | **3 %** | 47 % |
| moyenne (artefacts retirés) | 8,84R | 8,28R |

Mann-Whitney unilatéral p = 0,036 ; bootstrap de la différence de
médianes [−0,25 ; +2,64] — l'intervalle touche zéro. Le filtre tient,
sans marge. Son action principale est mécanique : il élimine la
population qui entre après le sommet.

Convergence indépendante : l'export d'alertes de la plateforme mesuré le
2026-08-18 montrait **299 déclenchements sur 299 sur un nouveau plus haut
du jour**, contre 4,7 % de taux de base. Deux chemins, même conclusion.

## 3. L'ambiguïté intra-barre — la bande de base de toute mesure OHLC

**26 % des fills sont structurellement indécidables** : le stop est touché
sur la barre d'entrée, et l'ordre trigger/stop est inconnaissable en
1 minute. Le benchmark indépendant sur tape d'août donnait **25 %**
(`research/momentum-replication/reports/2026-08-pine-v8-benchmark.md`).
Deux mesures indépendantes, même chiffre.

Espérance du ladder selon le traitement de ces 26 % :

| population | naïf | ambigus exclus | ambigus = −1R |
|---|---|---|---|
| tous (162) | +0,47R | +0,48R | +0,10R |
| NHD (62) | +0,71R | +0,64R | **+0,19R** |

L'ambiguïté coûte ~0,5R en pire cas mais ne fait pas basculer sous zéro.
Elle n'explique donc pas seule les backtests négatifs.

## 4. Le résultat durable — un échec de paramètre, pas de stratégie

Le stop médian de la population vaut **3,02 % du prix**. Le cap
`maxStopPct` était fixé à **3,0 %** — jamais sourcé dans le corpus, posé
exactement sur la médiane, éliminant **51 % des setups** et enfermant
tous les backtests dans la voie où la taxe d'exécution est maximale :

```
taxe en R = (spread + slippage en % du prix) / (stop en % du prix)
stop 3 %  →  0,5 % / 3 %  = 17 % de R par côté
stop 6 %  →  0,5 % / 6 %  =  8 % de R par côté
```

Cette direction a été **prédite avant la mesure**, puis retrouvée dans
deux surfaces indépendantes (ladder et participation, deux populations,
deux familles de sortie). Espérance du ladder NHD, en R :

| stop \ slippage | 0 % | 0,25 % | 0,5 % | 1 % |
|---|---|---|---|---|
| 1× (configuration historique) | +0,08 | −0,06 | **−0,20** | −0,49 |
| 1,5× | +0,33 | +0,23 | +0,14 | −0,06 |
| 2× | +0,34 | +0,27 | **+0,20** | +0,05 |
| 3× | +0,27 | +0,22 | +0,17 | +0,07 |

**−0,20R contre +0,20R, mêmes entrées, même population : c'est le stop qui
séparait les deux, pas la stratégie.** Ce qui est établi, c'est la marche
1× → plateau ; 1,5×-3× sont indiscernables sur 62 trades.

Une correction en route mérite d'être notée : deux sorties de structure
testées (`trail_dip`, `lower_highs`) ne se déclenchaient **jamais** — 0
déclenchement sur 37 — parce que le trailing partait sous le stop initial
élargi et n'y remontait jamais. Bug d'atteignabilité, pas règle lâche.
Corrigé (`stop = max(stop_initial, dernier_creux − 0,25×base)`), il
devient la meilleure sortie : +0,54R contre +0,42R pour tenir.

## 5. Le holdout — une exécution, protocole écrit d'avance

Candidat figé : premier repli conforme suivant un nouveau plus haut du
jour, stop à 2× la profondeur du dip, sortie `trail_fixed`, slippage
0,5 %/côté, 1 €/ordre, ambigus comptés −1R.

```
31 fills (>= 25, le résultat compte)
+0,69R   ·   +25,6 EUR/trade      -> au-dessus de la barre de +0,3R
queue : 13 % des fills >= +3R     -> SOUS le critère de 15 % figé d'avance
médiane -0,54R   ·   48 % de stops
```

Et la forme, calculée sur `data/holdout-trades.csv` :

- **DRCT seul porte 59 % du résultat total ; le top 3 en porte 128 %.**
  Sans ces trois trades, les 28 autres perdent 224 €.
- **8 pertes consécutives**, du 2026-06-15 au 2026-07-21.
- **Drawdown maximal 330 €, soit 10,9 %** du compte au plus haut.
- Depuis le 2026-06-01 : 16 trades, +181 € — **sans VERU, 15 trades à
  −164 €**. Le trimestre le plus récent est négatif à un trade près.
- La courbe affiche 2 000 → 2 793 €, **+40 %**. C'est le piège : un
  résultat superbe, injouable, parce que le chemin passe par huit pertes
  d'affilée et que les trois trades qui font l'année ne sont pas
  identifiables à l'avance.

## 6. Ce que l'étude n'a pas pu regarder

- **Détecter le megaday en temps réel.** Tout ceci est conditionné au fait
  de savoir d'avance que la journée en est un. Problème entier, jamais
  touché, et c'est lui qui décide de l'exploitabilité.
- **Le motif à 10 secondes**, invisible en barres 1 minute — nos « 3
  pullbacks conformes par jour » sont un plancher, pas un compte.
- **2022-2024**, absent faute de barres 1 min : l'échantillon penche
  vers 2025.
- **Les halts, les reprises, la lecture du prix indicatif** — techniques
  qu'il utilise et qu'aucune barre ne contient.
- n = 62 en tuning, 31 en holdout. Petit, et assumé comme tel.

## Verdict

**Bande du milieu du protocole : moteur de rejet, pas de génération de
signal.** La moyenne passe la barre, la forme non — et la forme était le
critère, écrit avant de connaître le chiffre.

Le rendement observé est un rendement de loterie sur une population de
loterie. Ce n'était pas une surprise disponible seulement après coup : le
rapport `research/momentum-replication/reports/2026-08-known-edges.md`
avait déjà rapproché nos propres 894 sessions de l'effet MAX documenté et
conclu qu'il était *largement inexploitable*. Deux méthodes indépendantes,
à un an d'intervalle, la même réponse.

Ce qui est acquis et ne dépend pas du holdout : **l'échec des backtests
historiques était un échec de paramètre**, un cap de stop jamais sourcé
posé sur la médiane de la population. Le corriger ne produit pas un edge —
il révèle la loterie qui était dessous.

Paper only. Une implémentation exacte n'est toujours pas un edge.
