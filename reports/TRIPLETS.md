# TRIPLETS.md

## LOTO MAROC Research Engine — Triplets (Phase 7)

Généré le 2026-10-01T11:27:20.562626+00:00. Pipeline (Cahier §17) : exploratoire -> filtrage (FDR-BH) -> confirmation hors-échantillon (split chronologique pré-spécifié, décidé avant tout calcul).

## OBSERVATION

- 18424 triplets possibles testés (probabilité théorique par tirage p=0.001086, test binomial EXACT — aucune simulation nécessaire, même argument que pour les numéros individuels en Phase 4 : probabilité constante par tirage, tirages indépendants).
- Effectif attendu par triplet sur l'échantillon d'exploration : ~1.71.
- Split pré-spécifié (avant tout calcul) : exploration = première moitié chronologique, confirmation = seconde moitié, jamais consultée au niveau exploratoire.
- Candidats après FDR-BH (exploration) : 0 / 18424.
- Confirmés hors-échantillon (Niveau C potentiel) : 0.

## CALCUL

### Top 10 (exploration, p brut le plus faible — à titre descriptif uniquement, PAS une liste de signaux)
  - 17-18-44 : count=9 (attendu 1.71), ratio=5.26, p_brut=7.4396e-05, p_ajusté=0.9243
  - 3-13-35 : count=8 (attendu 1.71), ratio=4.67, p_brut=0.00040135, p_ajusté=0.9243
  - 4-15-38 : count=8 (attendu 1.71), ratio=4.67, p_brut=0.00040135, p_ajusté=0.9243
  - 14-38-49 : count=8 (attendu 1.71), ratio=4.67, p_brut=0.00040135, p_ajusté=0.9243
  - 17-30-44 : count=8 (attendu 1.71), ratio=4.67, p_brut=0.00040135, p_ajusté=0.9243
  - 21-31-38 : count=8 (attendu 1.71), ratio=4.67, p_brut=0.00040135, p_ajusté=0.9243
  - 26-27-35 : count=8 (attendu 1.71), ratio=4.67, p_brut=0.00040135, p_ajusté=0.9243
  - 33-35-47 : count=8 (attendu 1.71), ratio=4.67, p_brut=0.00040135, p_ajusté=0.9243
  - 1-15-23 : count=7 (attendu 1.71), ratio=4.09, p_brut=0.0019344, p_ajusté=0.98566
  - 2-38-41 : count=7 (attendu 1.71), ratio=4.09, p_brut=0.0019344, p_ajusté=0.98566

### Candidats confirmés hors-échantillon (Niveau C, Cahier §2)
  Aucun.

## INTERPRÉTATION

- Un candidat qui survit à l'exploration (FDR-BH) MAIS PAS à la confirmation hors-échantillon est un faux positif probable : il n'est jamais présenté comme signal (Cahier §17).
- Un candidat confirmé dans les deux étapes atteint le Niveau C (anomalie robuste), jamais le Niveau D (pouvoir prédictif), qui exigerait une validation walk-forward complète (Phase 10).

## LIMITATION

- Les niveaux « filtrage » et « validation » du pipeline à 4 niveaux du Cahier sont fusionnés ici en une seule confirmation hors-échantillon.
- Le split 50/50 chronologique est un choix pré-enregistré parmi d'autres raisonnables (ex. 70/30) ; non reconsidéré après avoir vu les résultats.
- Tout candidat confirmé ici doit être ajouté à HYPOTHESES.md comme POST_HOC (Cahier §17, §21) : ce pipeline ne le fait pas automatiquement.
