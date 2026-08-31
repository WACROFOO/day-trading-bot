# Ross-style Momentum Trading Playbook

> Version consolidée : 30 août 2026  
> Usage : formation, simulation et construction d'un processus personnel — pas un conseil financier ni une promesse de résultat.

## 1. Objet, couverture et niveau de preuve

Ce document transforme le contenu étudié du cours **Warrior Pro Preview 2026 — Day Trading: The Basics** et la documentation des scanners Warrior en un système de décision utilisable. Il ne reproduit pas les vidéos, les transcripts ou les questionnaires propriétaires.

### Couverture réellement maîtrisée

- 19 vidéos ouvertes et traitées individuellement ;
- 12,91 heures de contenu ;
- 28 986 segments de transcript et 738 053 caractères analysés ;
- zéro unité vidéo manquante dans les chapitres 1 à 6 exposés par la Preview ;
- 153 questions visibles des six quiz étudiées sans soumettre ni modifier de réponse ;
- corrigé du chapitre 1 étudié ; les corrigés 2 à 6 sont restés verrouillés et n'ont pas été contournés.

La version complète du cursus **Day Trading: The Basics** comporte 15 chapitres. La Preview authentifiée examinée ne fournit les vidéos détaillées que pour les chapitres 1 à 6. Ce document ne prétend donc pas maîtriser les vidéos privées des chapitres 7 à 15.

### Légende de confiance

- **Confirmé cours** : règle explicitement enseignée dans les vidéos/quiz de la Preview.
- **Confirmé plateforme** : comportement documenté ou observé dans Day Trade Dash.
- **Approximation propre** : traduction transparente pour TradingView ; ce n'est pas le code source Warrior.
- **Paramètre personnel** : valeur à choisir après simulation et analyse statistique.

## 2. Identité de la stratégie

La stratégie étudiée est une approche **long-biased de momentum sur petites capitalisations américaines**. Elle cherche les titres évidents où une demande inhabituelle rencontre une offre limitée, puis attend une structure permettant de définir un risque court.

Le principe central est :

> Le scanner découvre un candidat. Le graphique définit le setup. Le stop définit la taille. Le marché décide du résultat.

Ce système n'achète pas simplement une action parce qu'elle monte. Il exige quatre couches successives :

1. **Sélection** : le titre satisfait au moins quatre des Five Pillars.
2. **Contexte** : catalyste, liquidité, daily chart et résistance laissent une opportunité réelle.
3. **Setup** : le 1 minute produit une première consolidation propre ou un micro pullback.
4. **Exécution** : entrée, invalidation, taille et sortie sont connues avant l'ordre.

## 3. Doctrine non négociable

1. Tester le processus en simulateur avant de risquer de l'argent réel.
2. Commencer en réel avec une taille minimale seulement après une série statistiquement cohérente en simulation.
3. Ne jamais transformer un objectif de revenu en obligation imposée au marché.
4. Rechercher les leaders évidents plutôt que forcer des actions secondaires.
5. Exiger au moins quatre piliers sur cinq ; rejeter normalement un score de trois sur cinq.
6. Préférer le premier mouvement propre et le premier pullback.
7. Ne jamais élargir le stop parce que le trade va contre le plan.
8. Si le breakout attendu ne se matérialise pas rapidement, réduire ou sortir plutôt que rationaliser.
9. Un setup valide peut perdre. La qualité du processus et la maîtrise de la perte sont les seules variables contrôlables.
10. Une plateforme, une connexion ou un ordre non maîtrisé est une raison de ne pas trader.

## 4. Entonnoir de sélection : les Five Pillars

### Seuils confirmés dans la Preview

| Pilier | Règle de travail | Pourquoi il compte |
|---|---|---|
| Prix | 2 à 20 USD ; zone statistiquement privilégiée 5 à 10 USD | Prix accessible et amplitude utile |
| Variation | Déjà en hausse d'au moins 10 % ; leaders privilégiés | La demande est visible |
| Relative Volume | Environ 5x ou plus | L'activité du jour est réellement anormale |
| Catalyste | Breaking news préférée mais pas obligatoire | Explique l'urgence et attire l'attention |
| Offre/demande | Float généralement inférieur à 20 M ; plus bas est préférable | Une faible offre amplifie la demande |

### Règle de décision

- **5/5** : meilleur alignement, mais toujours pas une entrée automatique.
- **4/5** : candidat acceptable si le graphique, la liquidité et le ratio rendement/risque confirment.
- **3/5 ou moins** : passer normalement.

Dans le scanner Warrior, les quatre piliers techniques peuvent être présents sans news. La flamme doit être vérifiée séparément.

### Ce que signifie réellement la flamme

La flamme indique l'âge d'une news récente, pas la conformité complète aux critères de Ross :

| Couleur | Âge indicatif de la news |
|---|---:|
| Rouge | 0 à 2 heures |
| Orange | 2 à 12 heures |
| Jaune | 12 à 24 heures |
| Aucune | Plus de 24 heures ou aucune news admissible |

La flamme ne mesure ni la qualité du catalyste, ni le float, ni le RVOL, ni le spread. Elle peut apparaître avec retard sur un scanner d'alertes. Une action avec flamme peut être un mauvais trade ; une action sans flamme peut produire un breakout technique valide.

## 5. Filtres de sécurité après les Five Pillars

Un candidat ne devient tradable qu'après les vérifications suivantes.

### Liquidité et exécution

- spread compatible avec le risque par action ;
- volume suffisant pour entrer et sortir sans distorsion excessive ;
- absence d'action « barcode » illiquide ;
- Level 2 et Time & Sales cohérents avec les transactions réelles ;
- taille adaptée à la liquidité, pas seulement au risque théorique.

### Daily chart et espace disponible

- identifier le plus proche niveau horizontal, trend line, gap/window, half-dollar, whole-dollar et daily 200 EMA ;
- privilégier un titre au-dessus des daily 9 EMA et 20 EMA, ou au minimum correctement basé ;
- préférer un titre au-dessus du daily 200 EMA ; s'il est dessous, exiger une distance réellement exploitable ;
- traiter une daily 200 EMA située à environ 0,50–1,00 USD comme une résistance potentiellement problématique, selon le prix et l'ATR ;
- vérifier qu'un objectif d'au moins 2R tient avant la première résistance probable.

### Catalyste et risque de dilution

- lire le titre complet de la news, l'heure et la source ;
- distinguer événement économique réel et communiqué promotionnel ;
- rechercher les financements, shelf registrations, warrants et manque de trésorerie ;
- ne pas considérer une news comme positive uniquement parce que le titre contient « partnership », « agreement » ou « AI ».

## 6. Matrice GO / WAIT / PASS

### GO : préparer l'ordre

- au moins 4/5 piliers ;
- titre parmi les leaders visibles ;
- spread et liquidité utilisables ;
- catalyste compris ou breakout technique clairement identifié ;
- daily chart avec espace ;
- première consolidation propre ;
- volume d'impulsion fort, volume de pullback plus faible ;
- entrée, stop et cible écrits ;
- potentiel d'au moins 2R avant la résistance pertinente ;
- taille calculée à partir du stop.

### WAIT : surveiller sans entrer

- mouvement initial sans pullback ;
- action trop étendue au-dessus de la 9 EMA/VWAP ;
- news pas encore comprise ;
- volume de breakout pas encore confirmé ;
- 5-minute encore ambigu alors que le 1-minute n'offre pas de risque propre ;
- vendeur important juste sous la cible ;
- prix proche d'une résistance, mais breakout possible si le volume revient.

### PASS : refuser le trade

- 3/5 piliers ou moins ;
- spread disproportionné ;
- volume faible ou action en « barcode » ;
- pullback de cinq ou six bougies qui traduit une perte d'intérêt ;
- volume rouge du pullback plus lourd que celui de l'impulsion ;
- stop logique trop éloigné ;
- résistance empêchant 2R ;
- daily chart avec rejet historique important au même niveau ;
- entrée envisagée uniquement par FOMO ;
- données figées, ordre incertain ou plateforme instable ;
- incapacité à expliquer l'invalidation en une phrase.

## 7. Setup principal : First Pullback

### Anatomie confirmée

1. Le titre répond à au moins quatre piliers et se trouve parmi les leaders.
2. Une impulsion produit une ou plusieurs bougies vertes fortes avec volume.
3. Le prix consolide normalement pendant **2 à 4 bougies**.
4. Le volume diminue pendant le pullback.
5. Une nouvelle bougie tente de dépasser le plus haut de la bougie précédente.

### Plan d'entrée

- **Trigger** : première bougie à faire un nouveau plus haut après le pullback.
- **Entry** : au-dessus du trigger, avec un buffer adapté au tick et au spread.
- **Stop structurel** : sous le plus bas du pullback ou de la structure signal.
- **Première cible** : retest du HOD ou prochaine résistance évidente.
- **Cible minimale de planification** : `Entry + 2 × risque par action`.
- **Cibles suivantes** : half-dollar, whole-dollar, résistance daily ou extension mesurée.

L'anticipation juste sous le trigger à l'aide du Level 2 et du tape est une technique avancée. Le modèle débutant attend la confirmation du nouveau plus haut.

### Profil de volume attendu

```text
Impulsion        Pullback         Breakout
volume élevé  -> volume réduit -> volume renouvelé
```

Si le volume rouge augmente pendant le pullback ou si le breakout se produit sans regain de volume, le signal perd en qualité.

### Invalidation

- rupture du plus bas du pullback ;
- gros vendeur qui bloque le niveau avant que le ratio attendu soit obtenu ;
- volume qui contredit la structure ;
- échec immédiat du breakout avec retour sous le trigger ;
- changement de contexte : halt, news négative, offering ou problème d'exécution.

## 8. Setup rapide : Micro Pullback

Le micro pullback est une consolidation d'une seule bougie rouge. Sur un graphique 10 secondes, plusieurs bougies peuvent former une petite pause à l'intérieur d'une bougie 1 minute entièrement verte.

### Conditions renforcées

- leader exceptionnellement fort ;
- volume et tape rapides ;
- structure 1-minute toujours constructive ;
- pas de résistance immédiate ;
- risque défini sur la micro-structure ;
- taille réduite si la vitesse ou le spread augmentent.

### Exécution

- entrée au premier nouveau plus haut de la micro-consolidation ;
- stop sous le bas de cette micro-structure ;
- HOD/première résistance comme cible initiale ;
- sortie rapide si l'accélération attendue n'apparaît pas.

Ce setup est plus rapide, plus sensible au slippage et moins adapté à un opérateur qui ne maîtrise pas encore les ordres et hotkeys.

## 9. Patterns secondaires et contexte

| Pattern | Lecture opérationnelle |
|---|---|
| ABCD | Impulsion, pullback, première tentative, consolidation, puis nouveau break de l'apex/HOD |
| Flat top breakout | Résistance testée plusieurs fois au même prix, puis cassée avec volume |
| Cup and handle | Récupération en U jusqu'à la résistance, puis petite consolidation/handle |
| Double top | Rejet près du sommet précédent ; confirmé seulement par l'échec et la faiblesse qui suit |

Ces formes ne remplacent ni les Five Pillars ni le plan de risque. Une belle forme sur une action sans attention, sans volume ou sans espace n'est pas le même setup.

## 10. Architecture graphique

### Hiérarchie des timeframes

| Graphique | Rôle |
|---|---|
| 10 secondes | Micro pullbacks et lecture très fine d'un mouvement exceptionnel |
| 1 minute | Graphique principal d'entrée, de stop et de management |
| 5 minutes | Contexte, maturité du mouvement et structure plus large |
| Daily | Espace, résistance, gaps/windows, EMA majeures et historique |

### Règles d'alignement

- meilleur cas : 1-minute et 5-minute constructifs ;
- bon 5-minute mais mauvais 1-minute : refuser normalement, car l'entrée et le risque sont imprécis ;
- excellent 1-minute avant la formation du 5-minute : possible sur un leader exceptionnel ;
- ne pas utiliser le bas d'une immense bougie 5-minute comme stop avec une taille normale ; réduire la taille si ce stop est réellement nécessaire.

### Indicateurs conservés

- **9 EMA** : tendance/support très court terme ;
- **20 EMA** : structure courte plus lente ;
- **200 EMA daily** : support/résistance majeure ;
- **VWAP** : équilibre intraday pondéré par le volume ; au-dessus = contrôle acheteur relatif ;
- **MACD 12/26/9 sur 1-minute** : confirmation du front side ; crossover négatif = ne plus presser agressivement ;
- **Volume** : valide ou invalide l'impulsion, le pullback et le breakout.

Les indicateurs confirment une hypothèse. Ils ne prédisent pas avec certitude.

## 11. Support, résistance, gaps et windows

### Niveaux à tracer avant l'entrée

- HOD et premarket high ;
- derniers pivots intraday ;
- plus hauts/bas daily récents ;
- half-dollars et whole-dollars ;
- daily 9, 20 et 200 EMA ;
- bords de gap/window ;
- trend lines ayant au moins deux points d'ancrage.

Un ancien niveau cassé peut changer de rôle : résistance devenue support, ou support devenu résistance.

### Gap versus window

- **Gap** : ouverture regular session sensiblement différente de la clôture précédente.
- **Window** : zone de prix avec peu de structure visible, créée par un vrai gap ou une très grande bougie.
- Une zone significative représente idéalement environ deux fois une bougie daily normale ou deux fois l'ATR daily.
- Le niveau récent prime sur un niveau ancien mineur. Analyser depuis le bord droit actuel vers la gauche.

## 12. News et catalystes

### Taxonomie étudiée

1. momentum technique sans news société ;
2. résultats ;
3. FDA ou résultats cliniques ;
4. buyout ;
5. split ou reverse split ;
6. objectif de cours ou changement de recommandation ;
7. prise de participation activiste ;
8. commande, contrat, accord ou partenariat ;
9. secondary offering ;
10. private placement ;
11. IPO ;
12. short interest élevé ;
13. brevet ou marque ;
14. uplist ou delist ;
15. SPAC, fusion ou acquisition ;
16. procès ou événement réglementaire ;
17. sentiment général du marché ;
18. sympathy move ou thème du moment.

### Questions à répondre en moins de 60 secondes

1. Qu'est-ce qui s'est produit ?
2. À quelle heure exacte ?
3. Est-ce nouveau ou déjà connu ?
4. L'événement a-t-il une valeur économique quantifiable ?
5. Existe-t-il un risque immédiat de dilution ?
6. Le marché valide-t-il la news par le volume et le prix ?

Une annonce importante peut produire un mauvais trade si le prix est déjà étendu ou si le buyout fixe presque toute la valeur restante. Une annonce ordinaire peut créer un grand mouvement si le float est extrêmement faible et la demande très forte.

## 13. Lecture rapide des SEC filings

| Filing | Utilité pratique |
|---|---|
| 10-Q | Situation financière trimestrielle |
| 10-K | Rapport annuel d'une société américaine |
| 20-F | Rapport annuel de nombreux émetteurs étrangers |
| S-3 | Shelf registration pouvant permettre des ventes futures d'actions |
| 13-D | Détenteur important, potentiellement activiste |
| 8-K | Événement matériel courant |
| Form 4 | Achat ou vente d'un insider |

Checklist dilution : trésorerie, cash burn, dette, actions en circulation, warrants, shelf actif, placements précédents et comportement des insiders. Un shelf est un drapeau de risque, pas la preuve qu'une offering est immédiate.

## 14. Scanner workflow

### Avant 9:30 ET

1. Ross's 5 Pillar Scan List / Top Gappers.
2. Top Gainers et Low Float Top Gainers.
3. Vérification de la flamme, de la news et du float.
4. Construction d'une watchlist courte avec niveaux daily et premarket.
5. Running Up autour des périodes de publication, notamment 7:00, 8:00 et 9:00 ET.

Les listes Top Gappers arrêtent leur mise à jour à 9:30 ET.

### Après 9:30 ET

1. Small Cap HOD Momentum.
2. Ross's Five Pillars Alert.
3. Running Up.
4. Top Gainers, Top Relative Volume et Change Since Open.
5. Top of Trend pour les reprises tardives et Power Hour.

### HOD Momentum : ce qui est connu et inconnu

Les branches visibles incluent low-float medium/high RVOL, Volatility Hunter, Former Momo, medium-float, 5 % en 5 minutes, 10 % en 10 minutes et 52-week breakout.

Les seuils exacts de chaque branche, la formule complète de momentum, le classement « Former Momo » et la normalisation RVOL du fournisseur ne sont pas publics. Toute copie TradingView doit rester étiquetée **approximation propre**.

## 15. TradingView : score et bandes de risque

### Score propre et transparent

Afficher séparément :

- prix dans 2–20 USD et drapeau idéal 5–10 USD ;
- variation depuis la clôture précédente >= 10 % ;
- daily RVOL >= 5x ;
- float vérifié < 20 M, ou proxy clairement étiqueté ;
- catalyste confirmé manuellement ;
- proximité HOD ;
- volume 5-minute ;
- espace jusqu'à la résistance daily.

TradingView Pine ne dispose pas d'un champ natif fiable pour reproduire la flamme de news. La news doit rester manuelle ou provenir d'un flux externe licencié.

### Construction correcte des bandes

Pour un first pullback confirmé :

```text
Entry       = trigger high + buffer
Stop        = pullback low - buffer
Risk/share  = Entry - Stop
Target 2R   = Entry + 2 × Risk/share
```

Hiérarchie des cibles :

1. HOD si le ratio reste acceptable ;
2. cible mécanique 2R ;
3. half-dollar/whole-dollar ;
4. résistance daily suivante.

Les bandes doivent être **figées sur la bougie signal confirmée** pour ne pas se déplacer avec chaque nouvelle bougie. Couleurs recommandées :

- bleu/cyan : zone d'entrée ;
- rouge : zone stop/invalidation ;
- vert : zone cible.

Une bande n'est affichée que lorsque le trigger choisi existe. Dans le script fourni, vérifier :

1. `Show entry / stop / target bands` activé ;
2. `Band trigger` réglé sur le signal souhaité ;
3. le symbole et le timeframe satisfont réellement ce signal ;
4. les plots/fills de l'indicateur ne sont pas masqués ;
5. les heures étendues sont activées pour analyser le premarket.

### Limite du modèle actuellement fourni

Le script propre peut armer ses bandes sur une bougie de signal HOD/Running Up. Le modèle Ross confirmé place idéalement le stop sous le **pullback complet**, pas automatiquement sous n'importe quelle bougie HOD. Une future version plus fidèle doit détecter et mémoriser la séquence 2–4 bougies, son plus bas et le premier nouveau plus haut.

## 16. Calcul de taille et risque

### Formules

```text
Risk/share brut     = Entry - Stop
Risk/share prudent  = Risk/share brut + réserve de slippage
Shares théoriques   = floor(Risque $ autorisé / Risk/share prudent)
Shares finales      = min(Shares théoriques, limite de liquidité)
Perte planifiée     = Shares finales × Risk/share prudent + coûts
```

Exemple pédagogique :

```text
Entry = 6,75
Stop  = 6,65
Risk/share = 0,10
HOD = 7,00
Reward potentiel = 0,25 = 2,5R
```

Pour un risque personnel autorisé de 25 USD et une réserve de slippage de 0,02 USD :

```text
Shares théoriques = floor(25 / 0,12) = 208
```

La taille réelle peut devoir être inférieure si le spread, la profondeur du carnet ou la vitesse rendent la sortie incertaine.

### Paramètres personnels à définir après backtest

- risque fixe par trade ;
- perte maximale journalière ;
- nombre maximal de trades ;
- perte maximale consécutive avant arrêt ;
- réserve de slippage par tranche de spread ;
- taille maximale par niveau de liquidité ;
- règles de réduction après une erreur d'exécution.

Le cours ne fournit pas une valeur universelle adaptée à chaque compte. Ces limites doivent protéger la survie et être testées en simulation.

## 17. Level 2, Time & Sales et exécution

- **Level 2** : ordres acheteurs/vendeurs affichés et encore non exécutés.
- **Time & Sales** : transactions réellement exécutées.
- Une offre visible peut être retirée ; le tape confirme si les transactions passent effectivement.
- Un gros vendeur sous la cible réduit l'espérance immédiate, surtout si les achats ne le consomment pas.
- Une accélération du tape au break soutient le signal ; un tape qui ralentit pendant l'échec appelle une sortie rapide.

### Ordres et fills

- distinguer quantité commandée et quantité exécutée ;
- traiter une partial fill comme une position réelle plus un ordre restant encore actif ;
- conserver les working orders dans une fenêtre séparée ;
- annuler explicitement tout ordre non désiré ;
- ne jamais supposer qu'un ordre disparu visuellement est annulé ;
- connaître l'effet FIFO sur P&L réalisé et lot restant.

## 18. Management du trade

### Avant le fill

- niveaux écrits ;
- taille calculée ;
- ordre et route testés ;
- résistance et HOD visibles ;
- scénario d'échec connu.

### Après l'entrée

1. Vérifier la taille réellement exécutée.
2. Confirmer ou placer l'ordre de protection selon le plan testé.
3. Observer la réaction au trigger et le regain de volume.
4. Ne pas élargir le stop.
5. Adapter la cible si un nouvel obstacle apparaît.
6. Si le breakout n'accélère pas, réduire ou sortir.

### Sorties

- **Stop structurel** : la thèse est invalidée.
- **Bailout** : la réaction attendue n'arrive pas assez vite.
- **Cible HOD/2R** : prendre selon le plan et la liquidité.
- **Partial** : autorisée seulement si définie et testée, pas improvisée sous l'effet du P&L.
- **Back side** : ne pas continuer à presser après dégradation du volume, rupture de structure et MACD 1-minute négatif.

## 19. Plan d'urgence

### Plateforme ou broker

1. essayer desktop, mobile puis portail web ;
2. vérifier les working orders et la position ;
3. appeler le broker si la situation n'est pas confirmée ;
4. capturer l'écran et l'heure des événements.

### Données ou graphiques

- utiliser une source indépendante ;
- surveiller le Level 2 et le tape du broker ;
- ne pas initier de nouveau trade avec des données douteuses.

### Infrastructure

- UPS pour modem, routeur et équipement critique ;
- hotspot ou connexion secondaire ;
- second ordinateur, téléphone ou tablette capable d'accéder au compte ;
- numéros du broker immédiatement disponibles.

## 20. Checklist de séance

### Avant le marché

- [ ] Plateforme, data, scanner et news en ligne.
- [ ] Connexion de secours et appareil secondaire prêts.
- [ ] Limites personnelles du jour écrites.
- [ ] Top gappers et leaders examinés.
- [ ] Five Pillars notés séparément.
- [ ] News et SEC filings pertinents lus.
- [ ] Float vérifié ou marqué comme inconnu/proxy.
- [ ] HOD, premarket high et résistances daily tracés.
- [ ] 1-minute, 5-minute et daily liés au même symbole.

### Avant chaque trade

- [ ] Au moins 4/5 piliers.
- [ ] Liquidité et spread acceptables.
- [ ] First pullback 2–4 bougies ou micro pullback qualifié.
- [ ] Volume cohérent.
- [ ] Entry ______
- [ ] Stop ______
- [ ] Risk/share ______
- [ ] Shares ______
- [ ] HOD ______
- [ ] Target 2R ______
- [ ] Prochaine résistance ______
- [ ] Scénario d'échec formulé.

### Après chaque trade

- [ ] Tous les working orders annulés ou intentionnels.
- [ ] Capture du scanner, de la news et des 1m/5m/daily.
- [ ] Setup et score Five Pillars enregistrés.
- [ ] Slippage, erreur et respect du stop enregistrés.
- [ ] Résultat en `R`, pas seulement en dollars.

## 21. Journal et statistiques

### Champs minimums

| Groupe | Champs |
|---|---|
| Contexte | date, heure ET, ticker, session, marché chaud/froid |
| Sélection | prix, gain %, RVOL, float, catalyste, score /5 |
| Setup | first pullback, micro pullback, ABCD, flat top, autre |
| Structure | nombre de bougies de pullback, volume, distance VWAP/EMA, résistance |
| Plan | entry, stop, cible, R attendu, shares |
| Exécution | fill moyen, slippage, partial fills, sortie |
| Résultat | P&L, R réalisé, MFE, MAE |
| Processus | règle respectée ?, erreur principale, capture, leçon |

### Mesures de maîtrise

```text
Win rate          = gagnants / trades
Average win (R)   = somme des R gagnants / gagnants
Average loss (R)  = somme des R perdants / perdants
Expectancy (R)    = Win rate × Avg win - Loss rate × Avg loss
Profit factor     = gains bruts / pertes brutes
Rule adherence    = trades conformes / trades totaux
```

Segmenter les statistiques par setup, heure, score Five Pillars, catalyste, float, RVOL et qualité daily. Une stratégie globalement rentable peut contenir un sous-groupe destructeur qu'il faut supprimer.

## 22. Programme de maîtrise sur 30 séances

### Séances 1–5 : reconnaissance

- identifier les Five Pillars sans prendre de trade ;
- expliquer chaque flamme et vérifier la news ;
- tracer HOD, VWAP, EMA et résistances daily ;
- classer chaque candidat GO, WAIT ou PASS.

### Séances 6–10 : replay

- rejouer uniquement des first pullbacks ;
- marquer trigger, pullback low et cible 2R ;
- comparer volume d'impulsion, de pullback et de breakout ;
- enregistrer le résultat théorique sans modifier les règles après coup.

### Séances 11–20 : simulateur

- un seul setup : first pullback ;
- risque personnel identique sur chaque trade ;
- arrêt immédiat après la limite journalière définie ;
- revue quotidienne avec résultats en R et respect des règles.

### Séances 21–25 : robustesse

- comparer premarket, ouverture et fin de matinée ;
- séparer marchés chauds et froids ;
- tester les effets du spread, slippage et partial fills ;
- conserver les règles, réduire la taille face à une liquidité inférieure.

### Séances 26–30 : validation

- calculer expectancy, profit factor et adherence ;
- vérifier que les gains ne viennent pas d'un seul trade extrême ;
- examiner tous les écarts de discipline ;
- n'ajouter le micro pullback que si le first pullback est exécuté proprement.

Le passage au réel n'est pas automatique à la trentième séance. Il dépend des données, de la stabilité du processus et de la capacité à respecter une perte prédéfinie.

## 23. Scénarios de décision

### Scénario A : quatre piliers sans flamme

`+18 %, prix 8 USD, RVOL 7x, float 12 M, aucune flamme.`

Le titre satisfait quatre piliers mesurables. Rechercher une news tardive, un thème ou un breakout technique. Ne pas rejeter automatiquement, mais ne pas entrer sans structure.

### Scénario B : first pullback propre

`Entry 6,75 ; pullback low 6,65 ; HOD 7,00.`

Le risque est 0,10 USD et le potentiel HOD 0,25 USD, soit 2,5R. Le trade reste conditionnel à la liquidité, au volume et à l'absence de résistance cachée.

### Scénario C : même pattern, mauvais volume

Les deux bougies rouges impriment plus de volume que l'impulsion. Le pattern nominal existe, mais le comportement des vendeurs l'invalide : PASS ou taille fortement réduite selon un plan testé.

### Scénario D : daily 200 EMA trop proche

`Prix 5,20 ; daily 200 EMA 5,50.`

La résistance potentielle n'est qu'à 0,30 USD. Si le stop nécessite 0,20 USD, la cible n'offre pas 2R avant cette barrière : PASS, sauf contexte exceptionnel explicitement testé.

### Scénario E : partial fill

Ordre 1 000, exécuté 200. Les 200 actions forment la position ; les 800 restantes peuvent être encore actives. Gérer séparément la position et le working order.

## 24. Questions de rappel actif

1. Pourquoi la flamme n'est-elle pas un score Ross ?
2. Quels sont les cinq piliers et leurs seuils Preview ?
3. Qu'est-ce qui différencie first pullback et micro pullback ?
4. Où se placent trigger, stop structurel et première cible ?
5. Quel profil de volume valide la structure ?
6. Pourquoi un titre 5/5 peut-il rester un PASS ?
7. Quand un bon 1-minute peut-il précéder un pattern 5-minute ?
8. Quel risque un S-3 signale-t-il ?
9. Pourquoi une flamme peut-elle être absente pendant les premières minutes ?
10. Que faut-il faire lorsqu'un ordre partiellement exécuté reste actif ?
11. Pourquoi faut-il figer les bandes sur le signal ?
12. Quelles mesures prouvent la maîtrise : dollars ou expectancy/adherence en R ?

## 25. Limites et prochains modules à étudier

Ce playbook couvre de façon traçable la Preview des chapitres 1 à 6 et la documentation accessible des scanners. Il ne prétend pas posséder :

- les vidéos privées non exposées des chapitres 7 à 15 ;
- le code source des scanners Warrior ;
- les seuils propriétaires de toutes les branches HOD/Volatility Hunter ;
- les paramètres personnels optimaux pour un compte donné ;
- une garantie que les règles historiques resteront performantes.

Toute règle nouvelle doit recevoir une étiquette claire : **confirmée**, **approximation** ou **hypothèse à tester**. L'objectif n'est pas de copier aveuglément une plateforme ; c'est de construire un processus propre, observable et falsifiable.

## 26. Inventaire des vidéos intégrées

| Chapitre | Vidéo | Durée approx. |
|---|---|---:|
| 1 | Becoming a Day Trader | 92:13 |
| 2 | Different Account Types for Traders | 39:09 |
| 2 | Choosing a Broker | 18:16 |
| 2 | Emergency Plan | 9:54 |
| 3 | Large Cap vs Small Cap vs Penny Stocks | 69:47 |
| 3 | Long- vs. Short-Selling | 54:43 |
| 3 | What Makes a Strong Stock? | 76:34 |
| 4 | Fundamental Analysis | 18:16 |
| 4 | SEC Filings | 21:02 |
| 4 | News Catalysts | 29:36 |
| 5 | Chart Types & Time Frames | 39:45 |
| 5 | Candlestick Shapes | 62:13 |
| 5 | Multi-Candlestick Chart Patterns | 46:49 |
| 5 | Support & Resistance | 40:07 |
| 5 | Gaps & Windows on Daily Charts | 25:32 |
| 5 | Popular Technical Indicators | 44:35 |
| 5 | Strong or Weak Daily Chart | 17:44 |
| 5 | Multi-Time-Frame Alignment | 25:32 |
| 6 | Trading Platform Walk-Through | 42:45 |

## 27. Résumé exécutable en 60 secondes

```text
SCAN
  Leader évident, $2-$20, +10 %, RVOL >=5x, float <20M, news vérifiée.

CONTEXT
  Spread/liquidité corrects, daily avec espace, 200 EMA et résistances tracées.

SETUP
  Impulsion forte -> pullback 2-4 bougies à volume réduit -> premier nouveau plus haut.

PLAN
  Entry au-dessus du trigger.
  Stop sous le pullback low.
  Shares = risque $ / risque par action prudent.
  Target = HOD ou au moins 2R, sans résistance bloquante.

EXECUTE
  Confirmer fill, working orders, volume et tape. Breakout ou bailout. Ne jamais élargir le stop.

REVIEW
  Captures, résultat en R, slippage, règle respectée, leçon unique.
```
