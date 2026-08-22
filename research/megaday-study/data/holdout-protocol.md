# Protocole holdout — écrit avant le lancer (2026-08-22)

Candidat figé sur le tuning (135 premiers megadays, cutoff 2025-09-10) :

**Entrée** : premier repli shape-valide (PARAMETERS.md) suivant un nouveau plus haut du jour (NHD), déclenchement au break de la dernière barre rouge.
**Stop** : 2× la profondeur du dip sous l'entrée (milieu du plateau 1,5×–3× ; ce qui est établi c'est la marche 1×→plateau, prédite d'avance par taxe = slippage/largeur).
**Sortie** : `trail_fixed` — trailing sur les creux qualifiants, `stop_courant = max(stop_initial, dernier_creux − 0,25×base)`. Choix verrouillé AVANT le holdout (mécanisme prédit par les 71 % de giveback, dominant une fois le bug d'atteignabilité corrigé). `hold` reste dans le rapport comme référence, pas comme candidat. Mesurer les deux et retenir le meilleur après coup serait une sélection sur données gelées — interdit.
**Coûts** : slippage 0,5 %/côté, commission 1 €/ordre, ambigus barre d'entrée comptés −1R (pire cas). Résultat rapporté en R **et en €/trade** (compte 2 000 €) — seule unité qui dit si c'est tradable.
**Budget d'hypothèses consommé** : 4 (NHD, largeur de stop, sortie, ladder vs hold). On n'ajuste plus rien après le holdout.

## Lecture du holdout (80 megadays gelés, 2025-09-10 → 2026-08-21)

- **moins de 25 fills → « non concluant »** — ni vert ni rouge, et on ne relance pas pour aller chercher mieux.
- **+0,3R ou mieux, avec la queue épaisse présente** → candidat retenu, on implémente.
- **0 à +0,3R** → l'outil reste un moteur de rejet, pas de génération de signal.
- **négatif** → la version mécanique est abandonnée ; les megadays auront servi à établir pourquoi.

**Critère chiffré de la queue** (figé depuis le tuning, qui en donne ~22 %) : la queue est présente si **≥ 15 % des fills atteignent +3R ou mieux**. En dessous, la forme n'y est pas, même si la moyenne est jolie.

Jugement sur la FORME (la queue, critère chiffré ci-dessus), pas sur le point :
le tuning donne ~78 % de trades à −1R et toute l'espérance dans 22 % — n=37 à 62,
+0,42R et 0,00R ne sont pas distinguables. Le holdout (~80 jours, ~50 fills attendus)
tranchera tout juste mieux.

Condition de validité de toute l'étude : elle suppose de *savoir que la journée est un megaday*.
Le holdout, même excellent, ne dit rien sur la capacité à trouver ces journées en temps réel à 09:30 —
problème resté entier, et c'est lui qui décide de l'exploitabilité.

Pronostic de l'opérateur, consigné avant le lancer : ~1 chance sur 3 de franchir +0,3R avec la queue ;
résultat le plus probable = bande du milieu (0 à +0,3R). Si ça dépasse, vérifier d'abord si 2-3 trades
portent tout.

Contrainte opérationnelle connue avant lancement : 3 pertes consécutives à 2 % de risque = −6 % du compte. Profil momentum classique, à assumer d'avance.

## Résultats tuning de référence (à comparer, pas à égaler)

- Ladder 1× + cap 3 % (config historique) : **−0,20R** à slip 0,5 % — l'échec des backtests était un échec de paramètre, pas de stratégie.
- Participation, 1er repli NHD, 2×, trail_fixed, slip 0,5 % : **+0,54R** (+19,5 €/trade).
- Marche 1×→2× présente dans les deux surfaces, deux populations, deux familles de sortie.
