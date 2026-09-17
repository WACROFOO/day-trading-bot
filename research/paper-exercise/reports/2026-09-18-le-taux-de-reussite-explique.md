# Le taux de réussite de 63 %, expliqué simplement

**D'OÙ VIENNENT LES CHIFFRES** · registre `journal.sqlite`, sessions du 11 au
17 septembre 2026 · 389 décisions enregistrées · 311 notées avec la suite du
marché · vérification de rejeu 389/389 · analysé le 18 septembre 2026

> ⚠ **Aucun ordre n'a jamais été envoyé.** Ces 19 trades n'ont pas existé.
> Ils sont reconstitués à partir des bougies d'une minute que le poste de
> travail a lui-même enregistrées. Ce document explique un calcul, il ne
> promet aucun gain.

---

## 1. Le mot « R », une seule fois

Tout est compté en **R**. Un R, c'est le risque prévu sur un trade, c'est-à-dire
**20 $** dans votre cas.

- Un trade perdant coûte **−1 R**, soit −20 $.
- Un trade gagnant qui atteint son objectif rapporte **+2 R**, soit +40 $.

Compter en R plutôt qu'en dollars permet de comparer un trade sur une action
à 3 $ et un trade sur une action à 13 $ : le risque est le même, 20 $.

## 2. D'où sortent les 19 trades

Les 389 décisions de la semaine ont toutes été rejetées, parce que le filtre
« actualité » tuait tout (le flux de news n'avait pas de clés). J'ai donc
repassé les 389 décisions dans les règles corrigées, avec exactement les
mêmes données qu'à l'instant où elles ont été prises.

Voici l'entonnoir, étage par étage :

```
389 décisions enregistrées pendant la semaine
│
├─ 191 restent rejetées        prix 88 · flottant 47 · déjà retombé 56
│                              (le filtre actualité en cachait 56 qui
│                               seraient mortes au filtre suivant)
│
└─ 198 auraient été autorisées
   │
   └─  53 « prospectives »     décisions prises sur des bougies vues en
       │                       direct. Les autres ont été armées sur
       │                       l'historique chargé au démarrage : elles ne
       │                       comptent pas, c'est la règle du protocole.
       │
       └─  51 ont touché le prix d'entrée
           │
           └─  19 étaient réellement prenables
                                32 des 51 arrivaient pendant qu'une autre
                                position était déjà ouverte. Une position à
                                la fois : elles étaient inaccessibles.
```

**Les 19, c'est ce qu'une seule personne, avec un seul compte, aurait pu
prendre dans l'ordre du temps.** C'est le seul chiffre honnête.

## 3. Le résultat des 19

| | |
|---|---:|
| trades gagnants | **12 sur 19** |
| **taux de réussite** | **63 %** |
| gain moyen par trade, avant frais | +0,83 R |
| gain moyen par trade, **après l'écart de prix** | **+0,60 R** |
| total | **+11,5 R, soit +229 $** |

L'« écart de prix » (le *spread*) est expliqué au §5. C'est le coût que vous
payez à chaque aller-retour, même quand vous ne vous trompez pas.

Le détail par jour :

| séance | trades | résultat |
|---|---:|---:|
| 11 septembre | 13 | **+11,0 R** |
| 15 septembre | 6 | +0,5 R |
| 14, 16, 17 septembre | 0 | — |

## 4. Pourquoi je ne crois pas à ce 63 %

Trois vérifications. Le chiffre en rate deux.

### ✗ ① Avec 19 trades, on ne sait rien

Statistiquement, la « vraie » moyenne se situe quelque part entre **−0,06 R
et +1,27 R**. Cet intervalle **contient zéro**. Autrement dit : avec si peu
de trades, un résultat comme celui-là est tout à fait compatible avec une
stratégie qui ne gagne rien du tout.

C'est comme lancer une pièce 19 fois, obtenir 12 faces, et en conclure que la
pièce est truquée. Elle ne l'est probablement pas.

### ✗ ② Ne rien faire aurait rapporté plus

Sur **exactement les mêmes 19 entrées**, aux mêmes instants :

| que faire après être entré | gain moyen | total |
|---|---:|---:|
| la stratégie (objectif à 2 R, stop sous le creux) | +0,60 R | +11,5 R |
| **garder jusqu'à la clôture** | **+1,04 R** | **+19,7 R** |

Garder la position sans rien faire aurait rapporté **0,43 R de plus par
trade**. L'objectif à 2 R coupe les gagnants trop tôt.

Ce n'est pas un détail : c'est précisément la **condition d'échec n° 2**
écrite dans le protocole le 6 septembre, avant de connaître ces chiffres.

### ✗ ③ Tout vient d'une seule journée

13 des 19 trades sont ceux du 11 septembre. Si on enlève cette seule journée,
il reste **6 trades, +0,5 R au total**, soit à peu près rien.

Et la concentration est extrême : 6 actions seulement, dont TNON à elle seule
6 trades sur 19.

## 5. L'écart de prix, en une minute

Une action a toujours **deux prix** en même temps :

- le **meilleur prix d'achat** proposé (ce que quelqu'un accepte de payer),
- le **meilleur prix de vente** proposé (ce que quelqu'un accepte de vendre).

Vous achetez au prix le plus haut des deux et vous revendez au plus bas.
L'écart entre les deux, vous le payez à chaque aller-retour.

**Exemple réel, VRA le 15 septembre :** entrée à 3,51 $, stop à 3,48 $. Votre
risque est donc de 3 cents par action. L'écart était de 1 cent. Vous achetez
à 3,51 $ alors que l'autre prix est à 3,50 $ : si vous revendiez une seconde
plus tard, sans que rien ne bouge, vous auriez déjà perdu **un tiers de votre
risque**.

Sur la semaine :

| | médiane |
|---|---:|
| écart de prix | 0,020 $ |
| risque prévu par action | 0,128 $ |
| **l'écart représentait** | **25 % de votre risque** |

Sur 39 trades mesurés, **5 avaient un écart plus large que le stop entier**.
Ce ne sont pas des trades, c'est de l'argent versé au marché.

## 6. Ce que ce calcul ne vérifie pas

- **Aucun ordre réel.** On suppose que vous entrez exactement au prix prévu.
  Sur une action rapide, l'ordre passe en réalité un peu plus haut.
- **Des bougies d'une minute.** Quand une bougie touche à la fois le stop et
  l'objectif, on compte le **stop** — le choix pessimiste, donc les chiffres
  ci-dessus ne sont pas flattés de ce côté-là.
- **Aucune suspension de cotation** n'a été détectée en cinq séances, ce qui
  est étonnant pour ces actions et reste inexpliqué.
- **Aucun frais de courtage** n'est compté (environ 0,05 à 0,07 R de plus).
- **Une seule semaine, un seul marché.**

## 7. Verdict

**63 % de réussite et +229 $ : le chiffre est exact, et il ne prouve rien.**

- Il repose sur 19 trades, dont 13 d'une seule journée.
- L'intervalle de confiance contient zéro.
- Ne rien faire du tout aurait rapporté davantage sur les mêmes entrées.
- Et l'étude sur onze ans de la même stratégie, dans ce même dossier, conclut
  à l'absence d'avantage, année après année, sans exception.

**Ce que ce chiffre montre vraiment, en revanche :** le filtre « actualité »
qui a tout tué pendant cinq séances ne sélectionnait rien d'utile. Les noms
qu'il a écartés se sont comportés comme les autres. Le défaut est corrigé, et
c'était la bonne décision — indépendamment de ce que valent ces 19 trades.

---

*Aucun ticket n'a été émis. Ce document ne valide ni un écart de prix réel,
ni un carnet d'ordres, ni des frais, ni une exécution. Compte de simulation
uniquement.*
