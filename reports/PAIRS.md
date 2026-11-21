# PAIRES.md

## LOTO MAROC Research Engine — Paires (Phase 7)

Généré le 2026-10-01T11:27:20.562626+00:00. Pipeline (Cahier §17) : exploratoire -> filtrage (FDR-BH) -> confirmation hors-échantillon (split chronologique pré-spécifié, décidé avant tout calcul).

## OBSERVATION

- 1176 paires possibles testés (probabilité théorique par tirage p=0.012755, test binomial EXACT — aucune simulation nécessaire, même argument que pour les numéros individuels en Phase 4 : probabilité constante par tirage, tirages indépendants).
- Effectif attendu par paire sur l'échantillon d'exploration : ~20.11.
- Split pré-spécifié (avant tout calcul) : exploration = première moitié chronologique, confirmation = seconde moitié, jamais consultée au niveau exploratoire.
- Candidats après FDR-BH (exploration) : 0 / 1176.
- Confirmés hors-échantillon (Niveau C potentiel) : 0.

## CALCUL

### Top 10 (exploration, p brut le plus faible — à titre descriptif uniquement, PAS une liste de signaux)
  - 11-41 : count=38 (attendu 20.11), ratio=1.89, p_brut=0.00027944, p_ajusté=0.32862
  - 17-44 : count=36 (attendu 20.11), ratio=1.79, p_brut=0.0010367, p_ajusté=0.60958
  - 28-40 : count=35 (attendu 20.11), ratio=1.74, p_brut=0.0022004, p_ajusté=0.86258
  - 10-33 : count=8 (attendu 20.11), ratio=0.40, p_brut=0.0033687, p_ajusté=0.98821
  - 8-30 : count=33 (attendu 20.11), ratio=1.64, p_brut=0.0067065, p_ajusté=0.98821
  - 8-22 : count=9 (attendu 20.11), ratio=0.45, p_brut=0.0093379, p_ajusté=0.98821
  - 5-40 : count=32 (attendu 20.11), ratio=1.59, p_brut=0.012815, p_ajusté=0.98821
  - 8-11 : count=32 (attendu 20.11), ratio=1.59, p_brut=0.012815, p_ajusté=0.98821
  - 11-18 : count=32 (attendu 20.11), ratio=1.59, p_brut=0.012815, p_ajusté=0.98821
  - 12-25 : count=32 (attendu 20.11), ratio=1.59, p_brut=0.012815, p_ajusté=0.98821

### Candidats confirmés hors-échantillon (Niveau C, Cahier §2)
  Aucun.

## INTERPRÉTATION

- Un candidat qui survit à l'exploration (FDR-BH) MAIS PAS à la confirmation hors-échantillon est un faux positif probable : il n'est jamais présenté comme signal (Cahier §17).
- Un candidat confirmé dans les deux étapes atteint le Niveau C (anomalie robuste), jamais le Niveau D (pouvoir prédictif), qui exigerait une validation walk-forward complète (Phase 10).

## LIMITATION

- Les niveaux « filtrage » et « validation » du pipeline à 4 niveaux du Cahier sont fusionnés ici en une seule confirmation hors-échantillon.
- Le split 50/50 chronologique est un choix pré-enregistré parmi d'autres raisonnables (ex. 70/30) ; non reconsidéré après avoir vu les résultats.
- Tout candidat confirmé ici doit être ajouté à HYPOTHESES.md comme POST_HOC (Cahier §17, §21) : ce pipeline ne le fait pas automatiquement.
