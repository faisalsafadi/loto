# TEMPORAL_REPORT.md

## LOTO MAROC Research Engine — Analyse temporelle (Phase 5)

Généré le 2026-09-29T18:41:14.978209+00:00. Dataset : DATASET_v001, 3155 tirages.

Toute différence entre périodes est qualifiée comme une différence de propriétés statistiques entre périodes, jamais comme preuve de fraude (Cahier des charges §19).

## OBSERVATION

- Tirages réellement consécutifs (amendement A5) : 3124 sur 3154 paires chronologiques (30 exclues : tirage absent entre les deux, ou écart calendaire > 4 jours).
- Moyenne observée de numéros communs entre tirages consécutifs : 0.7125 (référence théorique sous indépendance : 6×6/49 = 0.7347).
- Distribution des tailles d'intersection (0 à 6), sur 3124 paires : observé [1374, 1324, 378, 46, 2, 0, 0] vs hypergéométrique exacte [1362.0, 1290.3, 413.5, 55.1, 3.0, 0.1, 0.0].
- Effectifs par période (A3), 6 principaux :
  - 2001-2005 : 2994 tirages-numéros
  - 2006-2010 : 3114 tirages-numéros
  - 2011-2015 : 3108 tirages-numéros
  - 2016-2020 : 4326 tirages-numéros
  - 2021-2026 : 5388 tirages-numéros
- Effectifs par période (A3), complémentaire :
  - 2001-2005 : 499 tirages
  - 2006-2010 : 519 tirages
  - 2011-2015 : 518 tirages
  - 2016-2020 : 721 tirages
  - 2021-2026 : 898 tirages
- Rappel (amendement A6) : passage de 2 à 3 tirages/semaine entre 2015 et 2016, quasiment à la frontière des périodes 2011-2015 et 2016-2020 — cause connue à considérer en premier pour toute différence entre ces deux périodes précises.

## CALCUL

### H003 — Dépendance entre tirages consécutifs
- **Test PRIMAIRE (permutation, 20000 permutations, seed=42)** : p_value_permutation = **0.94615**
- Espérance sous H0 (permutée) : 0.7343 (écart-type 0.0136)

### H007 — Stabilité inter-périodes (test PRIMAIRE : χ² d'homogénéité période × numéro)
- 6 numéros principaux : χ²=178.990, df=192, p=0.7406
- Complémentaire : χ²=189.286, df=192, p=0.5418

### Runs test — parité de la somme (EXPLORATOIRE, amendement A2)
- n=3155 (pair=1569, impair=1586), suites observées=1558 (attendu 1578.45), z=-0.728, p=0.4663

## INTERPRÉTATION

- H003 et H007 sont évaluées par leur test PRIMAIRE pré-enregistré (permutation pour H003, χ² d'homogénéité pour H007) — aucune autre statistique n'est utilisée comme base de décision.
- Si H007 rejette H0 pour une comparaison touchant la frontière 2015/2016, le changement de fréquence des tirages (amendement A6) est l'explication de premier ordre à examiner avant toute autre interprétation (Cahier §18-19).
- Le runs test est EXPLORATOIRE (A2) : un résultat significatif ne devient pas confirmatoire sans être ajouté à HYPOTHESES.md comme POST_HOC et testé indépendamment.

## LIMITATION

- H003 exclut 30 paires chronologiques sur 3154 (tirage absent entre les deux ou écart calendaire trop grand) : le résultat porte sur les tirages réellement adjacents, pas sur l'ensemble de la séquence brute.
- H007 teste l'homogénéité globale des 49 fréquences entre périodes, pas une rupture datée précisément : une détection de rupture par change-point (CUSUM/`ruptures`) reste à faire séparément si H007 rejette H0 (hors du périmètre pré-enregistré de cette phase).
- Le runs test traite les tirages en séquence continue ; les tirages absents (A5) ne sont pas comblés, ce qui peut légèrement affecter le compte de suites sans invalider le test.

---

## ADDENDUM — Détection de rupture et autocorrélation par numéro

Ajouté le 2026-09-30T08:26:07.699854+00:00. Complète des actions de Phase 5 prévues au Cahier §19 et à l'EXECUTION_PLAN (CUSUM/ruptures, mémoire temporelle), omises au premier passage — identifiées en relisant `a_lire` (module « PHYSICS-BIAS » proposé, points 3, 4, 6).

### OBSERVATION

- CUSUM (test PRIMAIRE de cet addendum, permutation, 20000 perm., seed 42) sur la somme des 6 principaux : rupture la plus probable après le **2024-01-08** (moyenne avant=150.08, après=152.51), p=0.97290.
- CUSUM sur le complémentaire : rupture la plus probable après le **2003-08-23** (moyenne avant=27.29, après=24.56), p=0.52772.
- `ruptures.Pelt` (descriptif, sans p-value, pénalité BIC pré-spécifiée) — somme : {'breakpoints': [], 'penalty': 9008.009432608222, 'model': 'l2'} ; complémentaire : {'breakpoints': [255, 530, 1800, 1875], 'penalty': 1620.537939495644, 'model': 'l2'}.
- Autocorrélation lag-1 (EXPLORATOIRE, FDR-BH) : 0/49 numéros principaux et 2/49 valeurs du complémentaire significatifs après correction.

### INTERPRÉTATION

- La rupture CUSUM de la somme ne tombe PAS dans la fenêtre du changement de calendrier connu (2015-2016).
- La rupture CUSUM du complémentaire ne tombe PAS dans la fenêtre du changement de calendrier connu (2015-2016).
- Sous H0 (aucune structure), on attend ~2.5 faux positifs par famille de 49 tests avant correction : le nombre flagué après FDR-BH doit être interprété à cette aune.
- `ruptures.Pelt` est purement descriptif ici (pas de loi nulle calibrée pour sa pénalité) : il sert de recoupement visuel avec le CUSUM, pas de preuve indépendante.

### LIMITATION

- Le CUSUM ne détecte qu'UNE seule rupture dans la MOYENNE du signal ; un changement de variance ou de forme sans changement de moyenne, ou plusieurs ruptures successives, ne serait pas détecté par cette méthode seule (voir `ruptures.Pelt` en recoupement, lui aussi limité).
- Les tirages numérotés absents (~33, amendement A5) ne sont pas comblés dans la séquence utilisée : ils sont simplement absents, ce qui peut légèrement décaler la position exacte d'une rupture détectée.
- L'autocorrélation est EXPLORATOIRE (non pré-enregistrée avant la Phase 1) : tout numéro flagué ici doit être ajouté à HYPOTHESES.md comme POST_HOC avant toute investigation ultérieure, jamais présenté comme confirmatoire.

### SUIVI — calibration de ruptures.Pelt (2026-09-30)

Les 4 ruptures du complémentaire (2003-08-27, 2006-04-22, 2017-09-20, 2018-03-31) ont été converties
en dates puis la méthode (même règle de pénalité) a été calibrée sur 5000 séries synthétiques de bruit
pur (uniforme 1-49 avec remise, même n). Résultat : **P(≥4 ruptures sous H0) = 0.045** (5000 répétitions,
seed 42) — à la limite du seuil de 0.05, pas un résultat net.

**Décision : piste NON retenue, fermée sans investigation supplémentaire.** Motifs : (1) le CUSUM
(test primaire, hand-vérifié) ne détecte rien sur ce même signal (p=0.528) — désaccord avec `ruptures.Pelt`,
dont la pénalité est un choix heuristique non pré-enregistré ; (2) au vu du nombre total de tests réalisés
dans les Phases 3 à 5 (~35-40), un résultat isolé à p≈0.045 est exactement ce qu'attend le hasard, sans
correction multiple appliquée ici ; (3) aucune des 4 dates ne correspond à un changement connu (calendrier,
règles, matériel) - pas de mécanisme causal à tester. Enregistré dans HYPOTHESES.md pour traçabilité
complète, mais ne justifie aucune Phase 6/7 dédiée à cette piste.

