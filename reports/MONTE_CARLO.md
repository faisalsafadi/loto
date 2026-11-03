# MONTE_CARLO.md

## LOTO MAROC Research Engine — Moteur Monte-Carlo et test des gaps (Phase 6)

Généré le 2026-10-01T11:15:35.615371+00:00. Dataset : DATASET_v001, 3155 tirages. Seed : 42.

## OBSERVATION

- Moteur de simulation (`simulate_draws`, src/loto_research/simulation/monte_carlo.py) : reproductibilité vérifiée (même seed → résultats strictement identiques sur 20 historiques de test).
- Calibration : 770822 gaps simulés (numéro 1, 2000 historiques synthétiques de 3155 tirages) comparés à la loi géométrique exacte (p=6/49) : moyenne simulée 8.146 (théorique 8.167), χ²=28.75, p=0.4782 — le moteur reproduit correctement la loi théorique connue.
- H004 (principaux) : 0/49 numéro(s) significatif(s) après FDR-BH.
- Extension complémentaire : 0/49 numéro(s) significatif(s).

## CALCUL

### H004 — Distribution des gaps, 6 numéros principaux (test PRIMAIRE)
Référence : loi géométrique EXACTE de paramètre p=6/49 (pas de simulation nécessaire — la présence d'un numéro fixé est i.i.d. Bernoulli(p) d'un tirage à l'autre, tirages indépendants).
  Aucun numéro significatif après correction.

### Extension EXPLORATOIRE — Distribution des gaps, complémentaire
Référence : loi géométrique exacte de paramètre p=1/49.
  Aucun numéro significatif après correction.

## INTERPRÉTATION

- Le moteur `simulate_draws()` est validé par calibration (gaps simulés vs loi géométrique exacte) : il pourra être réutilisé pour la Phase 7 (paires/triplets), où aucune loi exacte simple n'existe pour les comparaisons envisagées.
- H004 est testée par sa loi de référence EXACTE, pas par Monte-Carlo : plus précis et moins coûteux qu'une simulation, dans l'esprit retenu depuis la Phase 3 (distributions exactes préférées à l'approximation quand elles existent).
- L'extension sur le complémentaire est EXPLORATOIRE (non pré-enregistrée) : tout numéro significatif devrait être ajouté à HYPOTHESES.md comme POST_HOC avant toute investigation ultérieure.

## LIMITATION

- Les gaps sont mesurés en nombre de tirages du dataset ANALYTIC (chronological_id), pas en jours civils ni en tirages officiels réels : les ~33 tirages absents (amendement A5) sont silencieusement sautés dans le décompte, comme pour H003.
- Un gap long observé ne doit JAMAIS être interprété comme une probabilité future accrue (Cahier §14, §18) : ce test vérifie seulement la compatibilité de la distribution des gaps passés avec le modèle nul, pas une quelconque prédiction.
- Les gaps ouverts en début/fin de série (avant la première apparition, après la dernière) sont exclus du test (convention standard, évite un biais de troncature).
