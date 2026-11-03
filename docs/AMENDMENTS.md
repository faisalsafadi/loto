# AMENDMENTS.md — modifications des spécifications après Phase 0

Toutes datées 2026-09-28, faites AVANT l'import des données (Phase 1). Additif : aucun texte existant supprimé.

| ID | Document | Objet | Motif |
|---|---|---|---|
| A1 | Cahier §12 ; IMPLEMENTATION_SPEC §15 | Loi nulle du χ² : espérance 43 (pas 48) ; référence = Monte-Carlo ; test de calibration sous synthetic_uniform | Tirage sans remise → indicateurs corrélés. Simulation : rejet à 5 % nominal = 0,85 % réel avec df=48 |
| A2 | IMPLEMENTATION_SPEC | Module information.py ; chi2/G/KL/entropie = une seule famille ; Fisher descriptive ; FFP écartée | Éviter d'inflater artificiellement le nombre de tests |
| A3 | IMPLEMENTATION_SPEC | Tests de permutation de l'ordre + Ljung-Box | Loi nulle exacte pour la dépendance temporelle |
| A4 | HYPOTHESES.md | Tests primaires par famille ; découpage temporel unique | Fixer les degrés de liberté avant les données |

Limite honnête : la loi exacte du χ² sans remise n'est qu'approximativement (43/48)·χ²(48) (variance simulée 72,2 vs 77,0). D'où la primauté du Monte-Carlo.
Ces amendements sont des propositions du responsable scientifique validées par l'utilisateur ; ils n'ont pas été appliqués au dépôt de l'utilisateur tant qu'il n'a pas copié les fichiers.

## A5-A6 (2026-09-28) — postérieurs à l'inspection de la structure du fichier, antérieurs à toute statistique sur les numéros
| ID | Objet | Motif |
|---|---|---|
| A5 | H003 : paires consécutives = N successifs et écart de dates ≤ 4 jours ; intervalles de H004 censurés à travers un tirage absent | ~42 tirages numérotés absents du RAW |
| A6 | H007 : changement 2 -> 3 tirages par semaine (2015-2016) déclaré cause connue, confondue avec la frontière 2011-2015 / 2016-2020 | Calendrier observé au diagnostic |

## A8 (2026-09-29) — postérieur à l'exécution de la Phase 4, rétractation d'un test invalide
| ID | Objet | Motif |
|---|---|---|
| A8 | [C] Phase 4 (biais de position) RÉTRACTÉ | 99,90% des lignes sont triées n1<...<n6 (statistiques d'ordre) : le test supposait un ordre de tirage réel, hypothèse fausse pour la quasi-totalité des données. §20 Cahier déclaré NON TESTABLE avec ces données. |

## Incident du 2026-09-29 — symlink Python casse par une mise a jour systeme
Une mise a jour systeme a repointe /usr/bin/python3 de 3.12 vers 3.14 (Python 3.14.4 desormais present
sur la machine). Le venv du projet (cree via `python3 -m venv`) avait enregistre ce chemin de maniere
relative (.venv/bin/python3 -> /usr/bin/python3), et a donc suivi le changement, cassant pytest/pandas/etc.
Aucun paquet n'a ete perdu (toujours present dans .venv/lib/python3.12/site-packages/) : seul le symlink
etait fautif. Correction : `ln -sf /usr/bin/python3.12 .venv/bin/python3` (repointage direct et explicite
sur l'executable versionne, plus robuste qu'un alias generique). Aucune re-execution des Phases 1-4
necessaire : l'environnement reel (interpreteur, bibliotheques, versions) n'a pas change, seul un lien
symbolique etait errone. requirements.lock.txt reste valide sans modification.

| A9 | Phase 9 | Pré-enregistrement des choix de modélisation, avant toute exécution : split temporel unique 80/20 par chronological_id (train id≤2524, test id>2524) ; alpha=10 pour le lissage bayésien du frequency_baseline ; remplacement du gap sentinel -1 par (chronological_id-1) avant régression logistique ; régression logistique sans recherche d'hyperparamètre (C=1.0, défaut scikit-learn) ; test primaire désigné à l'avance = Wilcoxon apparié sur le log loss par tirage ; famille de 3 comparaisons pré-enregistrées (frequency-vs-random, logistic-vs-random, logistic-vs-frequency) corrigée par Holm | Éviter tout p-hacking sur le choix de ces paramètres | Ce split unique N'EST PAS le walk-forward complet (réservé à la Phase 10) : H008 reste UNTESTED quel que soit le résultat de la Phase 9 |

| A10 | Phase 10 | Pré-enregistrement avant toute exécution (validé par l'utilisateur le 2026-10-04) : (1) fenêtre EXPANDING, pas rolling -- H007 (stabilité temporelle) rejetée en Phase 5, aucune rupture ne justifie d'écarter des données anciennes ; (2) MIN_TRAIN_DRAWS=500 (deja dans configs/default.yaml depuis la Phase 0, pas un nouveau choix) ; (3) baseline_random et frequency_baseline évaluées nativement sur tous les points 501..3155 (formules déjà causales/expanding, pas de "réentraînement" au sens strict) ; régression logistique réentraînée tous les 10 tirages (LOGISTIC_RETRAIN_STEP=10), prédictions gelées entre deux réentraînements ; (4) test_no_future_features() revérifié sur 20 points de contrôle répartis sur le walk-forward, pas à chaque itération (propriété du CODE, pas des données à un instant précis -- coût prohibitif sinon) ; aucun modèle plus complexe que la régression logistique testé (Phase 9 NO-GO, pas de justification) ; test primaire = log loss par tirage, Wilcoxon apparié + IC bootstrap (2000 réplications) sur la différence moyenne, 3 comparaisons pré-enregistrées (frequency-vs-random, logistic-vs-random, logistic-vs-frequency), correction de Holm, nouvelle famille propre à la Phase 10 (pas combinée avec celle de la Phase 9) | Ce walk-forward est le test OFFICIEL de H008 (Cahier §2, Niveau D) |

| E1 | Phase 10 (BACKTEST_REPORT.md) | Erratum : l'affirmation « deux échantillons disjoints » (Phase 9 vs Phase 10) est inexacte, la fenêtre de test de la Phase 9 étant incluse dans celle de la Phase 10 ; pas de réplication indépendante, REPLICATED non attribué | Découvert à la rédaction de FINAL.md (2026-10-08), sans effet sur la conclusion de la Phase 10 || E2 | Phase 5 / FINAL | Erratum : les 2 signaux d'autocorrélation lag-1 du complémentaire (TEMPORAL_REPORT, addendum du 2026-09-30) n'avaient pas été inscrits dans HYPOTHESES.md comme POST_HOC (H009) ; FINAL.md (réponses 3 et 4) et EXECUTIVE_SUMMARY.md les omettaient | Découvert à la relecture de TEMPORAL_REPORT.md (2026-10-08). Corrigé : H009 inscrite en EXPLORATORY, FINAL.md et EXECUTIVE_SUMMARY.md mis à jour. Sans effet sur les conclusions confirmatoires |
