### Phase 2 — Validation / nettoyage
STATUT : GO

Ce qui a été testé : conformité V001-V007 ligne par ligne, dates dupliquées (keep first), règle du
complémentaire (H002), construction du dataset ANALYTIC avec flags non bloquants (aucune correction).
Méthode : scripts/phase2_validate.py, exécuté par l'utilisateur ; 20 tests unitaires (pytest) passés
avant exécution (tests/test_validation.py, tests/test_cleaning.py).
Résultats (chiffres) :
- 3155 lignes RAW, 0 ligne vide, 0 ligne invalide (V001-V005), 0 date dupliquée.
- ANALYTIC = DATASET_v001, 3155 tirages, 2001-03-17 -> 2026-09-26.
- Flags non bloquants : N_GAP=21, WEEKDAY=7, N_NOT_INCREASING=6, N_RESET=6, DATE_GAP=4
  (cohérent avec le diagnostic structurel de la Phase 1).
- H002 (règle du complémentaire) : BONUS_IN_MAIN = 0/3155 (0,00%). Sous l'hypothèse d'un tirage
  indépendant (p=6/49), P(0 recoupement sur 3155 tirages) ~ 1e-179. Conclusion (amendement A7) :
  complémentaire exclusif des 6 principaux, loi marginale uniforme sur 49, test primaire H002 = chi2(48)
  classique, sans la correction 43/48 des amendements A1/A2 (spécifique aux 6 principaux).
Interprétation : le dataset ANALYTIC est prêt pour la Phase 3. Aucune ligne n'a été supprimée pour
anomalie de numérotation ou de calendrier : ces événements restent uniquement signalés (flags), pas nettoyés.
Limitations : draw_number_source reste non fiable comme identifiant (remises à zéro confirmées) ;
chronological_id et draw_id en tiennent lieu. Les ~33-35 tirages numérotés absents ne sont pas reconstitués.
Explication alternative envisagée : aucune nécessaire ici (résultat quantitatif univoque pour H002).
Fichiers produits : data/validated/{invalid_records,duplicate_dates,removed_duplicate_dates}.csv (vides),
data/analytic/draws.parquet (DATASET_v001), data/analytic/dataset_manifest.json, reports/DATA_QUALITY_REPORT.md,
logs/run_phase2_*.json.
Décision : GO. 3155 tirages valides utilisés pour la suite. Passage à la Phase 3 (analyse statistique
fondamentale) sur confirmation explicite de l'utilisateur.
