# Étape 3 — typage post-mortem des journées

**CONTRAINTE : le holdout est consommé. Cette étape produit une HYPOTHÈSE, jamais une validation.**
Toute validation future demande des données neuves (forward, ou 2022-2024 si les barres 1-min sont retrouvées). Pas de re-tune + re-test sur ces jours.

**Critère de lecture, écrit avant de regarder** :
- les types séparent nettement (un type porte les gros gagnants, un autre les séries de pertes) → hypothèse pour un forward test, et on sait quelles données collecter ;
- pas de séparation → le plan est terminé, la réponse reste « moteur de rejet », l'effort part vers la détection temps réel.
- n par type affiché ; un type à 5 journées ne prouve rien.

Variables de typage connues à 09:45 uniquement. Substitution notée : le gap % (close veille indisponible dans le repo) est remplacé par le change pré-market 04:00→09:30.

## Population: 98 jours typés (tuning 45, holdout 53)

Distribution des types (tous jours) :

- PM+/drive_up: 35
- PM-/drive_down: 26
- PM-/drive_up: 22
- PM-/range: 8
- PM+/drive_down: 7

## Q1 — DRCT, VERU, INHD sont-ils du même type ?

ticker       date         type  pm_change_pct  pm_high_broken    dir15  halt_before_945    R
  DRCT 2025-11-13    PM-/range            1.0           False    range             True 11.7
  VERU 2026-06-04    PM-/range           -3.1           False    range             True  8.7
  INHD 2026-04-08 PM+/drive_up           -2.3            True drive_up             True  5.2

## Q2 — les 8 pertes consécutives (2026-06-15 → 2026-07-21) sont-elles concentrées ?

ticker       date           type     R
  PAVS 2026-06-15 PM-/drive_down -1.06
  CLWT 2026-06-17 PM-/drive_down -1.04
  ICCM 2026-06-17   PM-/drive_up -1.02
  PLSM 2026-06-24   PM-/drive_up -1.03
  CELZ 2026-06-30   PM+/drive_up -1.07
  CLRO 2026-07-02   PM-/drive_up -0.54
  LGHL 2026-07-14   PM+/drive_up -1.07
   OMH 2026-07-21      PM-/range -1.03

Types des pertes: {'PM-/drive_down': 2, 'PM-/drive_up': 3, 'PM+/drive_up': 2, 'PM-/range': 1} vs population holdout: {'PM+/drive_up': 11, 'PM-/drive_down': 6, 'PM-/range': 3, 'PM-/drive_up': 8, 'PM+/drive_down': 2}

## Q3 — taux de base par type (R moyen, n affiché)

| type | n (avec R) | R moyen | R médian | % positif |
|---|---|---|---|---|
| PM+/drive_down | 3 | +2.92 | +0.86 | 100% |
| PM+/drive_up | 24 | +4.11 | +1.34 | 79% |
| PM-/drive_down | 15 | +6.40 | +1.45 | 73% |
| PM-/drive_up | 17 | +2.21 | +1.56 | 59% |
| PM-/range | 5 | +5.53 | +8.27 | 80% |

Variables secondaires, mêmes stats :

**halt_before_945**

| valeur | n | R moyen | R médian |
|---|---|---|---|
| False | 14 | +6.57 | +2.23 |
| True | 50 | +3.53 | +1.16 |

**price_band**

| valeur | n | R moyen | R médian |
|---|---|---|---|
| 10-20 | 8 | +6.96 | +0.69 |
| 2-5 | 22 | +3.01 | +0.27 |
| 5-10 | 12 | +2.77 | +1.72 |
| >20 | 22 | +5.15 | +1.89 |

## 3c — taux de base par numéro de dip et par heure (tuning NHD)

| dip n° | n | MFE médian (R) | P(≥1R) |
|---|---|---|---|
| 1 | 37 | 1.98 | 78% |
| 2 | 17 | 1.85 | 82% |
| 3 | 6 | 7.71 | 83% |

| heure entrée (ET) | n | MFE médian (R) | P(≥1R) |
|---|---|---|---|
| 09h | 9 | 4.40 | 89% |
| 10h | 14 | 1.60 | 79% |
| 11h | 9 | 3.06 | 89% |
| 13h | 5 | 1.83 | 80% |
