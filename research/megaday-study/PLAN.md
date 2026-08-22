# Étude des 250 megadays — plan détaillé

> **Étude terminée. Résultat et verdict : `RESULTS.md`.** Le plan ci-dessous
> a été suivi tel quel ; le protocole de lecture du holdout a été figé avant
> de le lancer et n'a pas été révisé après.

```
ACTIF · 250+ sessions "megaday" en barres 1 minute, chacune datée par la
     tape (research/challenge-tickers/corpus-megadays.csv).
POURQUOI CE PLAN · trois mesures de ce repo disent la même chose : 894
     sessions à espérance négative, 3 des 61 trades qu'il a lui-même
     nommés survivent à nos règles d'entrée, et chaque desserrage de
     gate testé ajoute des perdants. Régler des seuils sans connaître le
     taux de base, c'est le cercle. Ce plan établit d'abord la base,
     ensuite seulement les règles.
BIAIS DU DATASET · ces journées sont sélectionnées PARCE QUE le titre a
     bougé. Le dataset répond donc à « comment trader un megaday », pas
     à « ce titre va-t-il faire un megaday ». La sélection en temps réel
     est un problème séparé, et il n'est pas résolu ici.
PAPER ONLY.
```

## Étape 0 — Geler le holdout AVANT de regarder

- Réserver **80 sessions**, choisies **chronologiquement** (les plus
  récentes), et ne plus jamais les ouvrir jusqu'à l'étape 5.
- Écrire la liste gelée dans un fichier daté et versionné.
- Travailler sur les ~170 restantes.

Pourquoi chronologique plutôt qu'aléatoire : un tirage aléatoire mélange
les régimes et rend le holdout trop facile. Les 80 plus récentes
ressemblent le plus au marché que tu vas trader.

Pourquoi maintenant : leur propre test montre +0,4–1,4R en tuning qui
tombe à +0,1–0,6R en holdout. Cette décroissance est la signature de
l'ajustement au bruit. Le seul remède est un holdout jamais regardé.

## Étape 1 — L'anatomie (descriptif, aucune stratégie)

Aucune règle d'entrée, aucun trade simulé. On décrit l'objet.

| question | mesure |
|---|---|
| Quand le move a-t-il lieu ? | heure du plus haut du jour ; part du range faite avant 09:30 |
| Reste-t-il quelque chose après l'ouverture ? | % du range du jour encore disponible à 09:35, 09:45, 10:00, 11:00 |
| Combien de jambes ? | nombre de séquences push→dip→push par journée |
| À quoi ressemble un dip ? | profondeur en % du push, durée en barres, ratio de volume dip/push |
| Comment ça finit ? | clôture en % du plus haut ; heure du plus haut vs heure du plus bas de l'après-midi |
| Contexte | gap %, prix, volume, nombre de halts (trous > 2 min) |

Ce que ça sert : ça tue des branches entières pour pas cher. Si la
médiane du range est faite avant 09:30, une stratégie RTH se bat pour
les miettes et il faut le savoir avant d'optimiser quoi que ce soit.

## Étape 2 — Le taux de base (la pièce manquante)

**Prendre TOUS les breakouts de dip, sans un seul gate.**

- Shape seule : une poussée, 1 à 3 barres de repli, déclenchement au
  dépassement du plus haut de la barre précédente.
- Stop : bas du dip. Sortie : une seule politique de référence
  (moitié à +1R, stop à l'entrée, reste à +2R).
- Résultat en **R**, pas en euros — la taille ne doit pas polluer la mesure.

À rapporter :
- n, taux de réussite, **R moyen ET R médian**, somme des R
- la **distribution** des R, pas seulement la moyenne : quelques monstres
  qui portent tout ≠ une grinderie régulière, et ça change toute la suite
- distributions MFE / MAE
- le taux de base **par numéro de dip** (1er, 2e, 3e...) et **par heure**

À partir de là, chaque gate a une seule question à répondre :
**bats-tu le fait de tout prendre ?** La plupart ne le feront pas, et ils
sautent sans discussion. C'est ce chiffre qui manque aujourd'hui, et son
absence est exactement pourquoi on tourne en rond.

## Étape 3 — Segmenter les JOURNÉES, pas les setups

En deux temps, et l'ordre compte.

**3a. Est-ce que des types existent ?** Regrouper les 170 journées par
forme observée : gap-and-go du matin, spike de midi sur news, journée à
halts en série, runner multi-legs, pump qui meurt à 10h. Puis calculer le
taux de base **par type**.

Hypothèse à battre : la stratégie est positive sur un ou deux types et se
fait massacrer sur les autres, et le résultat global négatif n'est que la
moyenne des deux.

**3b. Le type est-il identifiable À TEMPS ?** C'est la question qui décide
si 3a sert à quelque chose. Le type doit être reconnaissable avec ce qu'on
sait **avant de trader** — gap, volume pré-market, prix, flottant, heure
du premier halt — et pas avec l'heure du plus haut, qui n'est connue qu'à
la fin. Si le type n'est pas identifiable à 09:45, c'est une jolie
classification inutilisable.

Si 3a et 3b passent tous les deux : **la stratégie n'est pas dans
l'entrée, elle est dans le tri des journées.** Ce qui colle avec lui — il
passe sa matinée à choisir, pas à régler des indicateurs.

## Étape 4 — Trois à cinq hypothèses, écrites d'avance

~800 setups autorisent honnêtement **3 à 5 tests**, pas quinze. Les
choisir maintenant, les écrire, et s'y tenir.

| # | hypothèse | pourquoi elle mérite une place |
|---|---|---|
| H1 | La sortie fixe 1R/2R coûte de la performance face à « vendre dans la force » | jamais mesuré ici ; le ladder est NOTRE invention, pas la sienne — lui vend sur les niveaux de halt et dans l'extension |
| H2 | Le taux de base est positif sur le type de journée X | c'est le pari principal de l'étape 3 |
| H3 | Le 1er dip bat le 2e et le 3e | règle sourcée chez lui, jamais vérifiée sur nos données |
| H4 | Le placement du stop (bas du dip vs ATR vs % fixe) change l'espérance | le cap à 3 % est un ajout local non sourcé |
| H5 | La contrainte horaire ajoute ou retire | déjà testée sur 11 jours (elle retirait), à confirmer sur 250 |

Tout se teste **sur les 170 seulement**.

## Étape 5 — Une seule passe de validation, et une décision écrite d'avance

Un tir unique sur les 80 sessions gelées. Pas de re-tuning après, quoi
qu'il arrive.

Et la règle de décision se fixe **maintenant**, pas après avoir vu le
résultat :

- espérance holdout **> +0,3R** par trade : il y a quelque chose, on
  passe à l'implémentation Pine du sous-ensemble qui marche ;
- entre **0 et +0,3R** : trop faible pour survivre aux frais et au
  slippage réel — on garde l'outil comme moteur de rejet ;
- **négative** : la version mécanique est abandonnée. L'indicateur
  devient un scorecard (rejets, journal, discipline) et l'effort part
  ailleurs. Ce n'est pas un échec, c'est un résultat.

## Hygiène des données, non négociable

- **Splits** : une barre dont le plus bas est sous 25 % de la clôture est
  un print post-reverse-split, pas un move (CRKN 2026-08-13 : bas
  $0,0002 pour une clôture à $0,0003 = « range » de 49 900 %).
- **Halts** : un trou de plus de 2 minutes en séance = halt. Un stop ou
  une cible à l'intérieur du trou n'est pas exécutable ; ces trades sont
  marqués, pas comptés comme normaux.
- **Séquence intrabar** : quand une barre touche le déclencheur ET le
  stop, l'ordre des deux est inconnu depuis de l'OHLC. Ces cas sont
  comptés et déclarés — sur tape réelle ils représentaient 25 % des fills.
- **Pas de re-fit après le holdout.** Une seule passe.

## Ce que cette étude ne peut pas répondre

- Choisir le megaday **en temps réel** — le dataset est conditionné sur
  le fait que le move a eu lieu.
- Le motif à 10 secondes — invisible en barres 1 minute.
- Halts, reprises, lecture du prix indicatif : trois techniques d'entrée
  qu'il utilise et qu'aucune barre ne contient.
