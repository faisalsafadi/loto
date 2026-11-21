# STATISTICAL_REPORT.md

## LOTO MAROC Research Engine — Analyse statistique fondamentale (Phase 3)

Généré le 2026-09-29T00:13:52.717258+00:00. Dataset : DATASET_v001, 3155 tirages, 2001-03-17 -> 2026-09-26.

Aucun numéro n'est qualifié de « chaud » ou « froid » avec implication prédictive à ce stade (Cahier des charges §11) : ce rapport est descriptif et confirmatoire, pas prédictif.

## OBSERVATION

- 6 numéros principaux : 18930 tirages-numéros au total sur 49 numéros, attendu 386.33 par numéro.
- Numéro(s) les plus fréquents : 41 (433, z=+2.53), 15 (416, z=+1.61), 44 (412, z=+1.39), 47 (411, z=+1.34), 8 (406, z=+1.07)
- Numéro(s) les moins fréquents : 13 (355, z=-1.70), 32 (358, z=-1.54), 14 (361, z=-1.38), 24 (363, z=-1.27), 25 (364, z=-1.21)
- Complémentaire : attendu 64.39 par numéro sur 3155 tirages.
- Somme des 6 numéros : moyenne observée 150.403 (théorique exacte 150.000), écart-type observé 33.443 (théorique 32.787).

## CALCUL

### H001 — Équirépartition des 6 numéros principaux
- χ² naïf (df=48, RAPPORTÉ À TITRE INDICATIF SEULEMENT, cf. amendement A1) : χ²=32.280, p=0.9602
- **Test PRIMAIRE (Monte-Carlo, 100000 simulations, seed=42)** : p_value_monte_carlo = **0.89854**
- Espérance de la statistique sous H0 (simulée) : 43.04 (écart-type 8.80) — référence théorique ≈43 (PAS 48, amendement A1).

### H002 — Équirépartition du complémentaire
- **Test PRIMAIRE (χ²(48) classique, amendement A7 — complémentaire confirmé exclusif des 6 principaux en Phase 2, loi marginale uniforme sur 49)** : χ²=69.355, p=0.0235

### Somme des 6 numéros (distribution EXACTE par dénombrement, pas d'approximation CLT)
- χ² vs distribution exacte : χ²=202.980, df=184, p=0.1607 (259 classes -> 185 après fusion des queues, effectif attendu < 5)

### Pair/impair (distribution EXACTE hypergéométrique)
- χ²=10.782, df=6, p=0.0954
- Observé : {0: 33, 1: 264, 2: 702, 3: 1042, 4: 777, 5: 280, 6: 57}
- Attendu : {0: 30.4, 1: 239.7, 2: 719.2, 3: 1050.3, 4: 787.7, 5: 287.7, 6: 40.0}

### Bas (1-24) / haut (25-49) (distribution EXACTE hypergéométrique)
- χ²=5.899, df=6, p=0.4346

## INTERPRÉTATION

- H001 et H002 sont évaluées par leur test PRIMAIRE pré-enregistré (Monte-Carlo pour les 6 principaux, χ²(48) pour le complémentaire) — les statistiques asymptotiques naïves sont rapportées uniquement à titre indicatif, jamais comme base de décision.
- Un résultat non significatif ici (p élevé) est une absence de preuve de structure, pas une preuve d'absence — voir les Phases 4 à 7 pour les tests de structures plus fines (paires, triplets, ruptures temporelles).
- Le statut UNTESTED de H001/H002 dans HYPOTHESES.md doit être mis à jour manuellement après revue de ce rapport (pas automatiquement par ce script).

## LIMITATION

- La variance utilisée pour les z-scores descriptifs par numéro (IMPLEMENTATION_SPEC §14) est MARGINALE et ne tient pas compte des corrélations négatives entre numéros dues au tirage sans remise (voir amendement A1) : elle sert à une lecture rapide, pas de test formel.
- Les ~33 tirages numérotés absents (amendement A5) ne sont pas inclus : ce rapport porte sur les 3155 tirages réellement présents dans DATASET_v001, pas sur un historique complet reconstitué.
- Run Monte-Carlo : OFFICIEL (100000 simulations, seed 42, 104.7s).
