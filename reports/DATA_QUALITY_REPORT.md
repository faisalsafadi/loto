# DATA_QUALITY_REPORT.md

## LOTO MAROC Research Engine — Rapport qualité (Phase 2)

Généré automatiquement. Aucune valeur n'a été corrigée ; toute anomalie est
signalée (flag) ou exportée (invalid_records.csv / duplicate_dates.csv), jamais supprimée silencieusement.

## OBSERVATION
- Lignes de données dans le RAW (hors en-tête, hors lignes entièrement vides) : 3155
- Lignes entièrement vides ignorées : 0
- Nombre de tirages attendu (Cahier des charges) : 3159
- Écart RAW vs attendu : -4 (voir PHASE_1_REPORT.md — accepté formellement par l'utilisateur le 2026-09-28)
- Lignes invalides (V001–V005) : 0
- Lignes concernées par une date dupliquée : 0 ; supprimées de l'ANALYTIC (keep first) : 0
- Lignes dans le dataset ANALYTIC final : 3155
- Première date : 2001-03-17
- Dernière date : 2026-09-26
- Années représentées : [2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]

## CALCUL — répartition des lignes invalides par règle
- Aucune ligne invalide détectée (0 ligne V001–V005).

## CALCUL — signalements non bloquants (flags), dataset ANALYTIC
- Total de signalements : 44
- N_GAP : 21
- WEEKDAY : 7
- N_NOT_INCREASING : 6
- N_RESET : 6
- DATE_GAP : 4

## INTERPRÉTATION — règle du numéro complémentaire (Cahier §6, H002)
- BONUS_IN_MAIN (complémentaire == un des 6 principaux) : 0 / 3155 tirages (0.00%)
- Aucune source officielle trouvée (RESEARCH_REVIEW.md) ne précise explicitement si le complémentaire
  est tiré parmi les 43 numéros restants ou indépendamment parmi les 49.
- Règle de décision, fixée AVANT ce calcul (non post-hoc) :
    taux observé ≈ 0 %  -> complémentaire exclusif des 6 principaux (tirage sans remise étendu) ;
    taux observé ≈ 12,24 % (6/49) -> tirage du complémentaire indépendant, avec remise possible.
    tout taux intermédiaire reproductible -> anomalie à investiguer (Phase 4), pas une règle du jeu.

## LIMITATION
- Le fichier source a été modifié par l'utilisateur avant import (voir PHASE_1_REPORT.md) ; les
  modifications ne sont pas documentées. Le RAW n'est donc pas la sortie brute originale du site.
- Les tirages numérotés mais absents (~42, cf. diagnostic Phase 1) ne sont ni comptés comme invalides
  ni reconstitués : ils sont simplement absents du dataset, ce qui affecte H003/H004 (voir amendement A5).
- draw_number_source n'est PAS un identifiant global (numérotation remise à zéro plusieurs fois,
  cf. diagnostic Phase 1) : chronological_id et draw_id en tiennent lieu (IMPLEMENTATION_SPEC §7).
