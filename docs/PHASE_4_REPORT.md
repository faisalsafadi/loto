### Phase 4 — Recherche d'anomalies
STATUT : GO

Ce qui a été testé : [A] frequence par numero principal (49 tests binomiaux exacts, Holm - pre-enregistre
H001) ; [B] frequence par numero du complementaire (49 tests binomiaux exacts, FDR-BH - exploratoire) ;
[C] biais de position n1-n6 (6 tests chi2(48), Bonferroni - exploratoire, RETRACTE en cours de phase).
Méthode : scripts/phase4_anomalies.py, scripts/diagnostic_position_order.py (diagnostic post-hoc en
lecture seule). 10 tests unitaires passes avant execution.
Résultats (chiffres) :
- [A] 0/49 numero de niveau B apres correction Holm.
- [B] 0/49 numero de niveau B apres correction FDR-BH (le signal global de H002, p=0.0235, Phase 3,
  n'est donc porte par AUCUN numero individuel apres correction : signal diffus, pas localise).
- [C] RETRACTE : chi2 enormes (1907-7980, df=48, p=0 aux 6 positions) causes par un modele nul invalide.
  Diagnostic : 3152/3155 lignes (99.90%) triees n1<...<n6 (statistiques d'ordre, jamais uniformes par
  construction). n1=minimum dans 100% des cas, n6=maximum dans 99.94%. Amendement A8.
Interprétation : aucune anomalie de frequence retenue. Le fait que le signal H002 (Niveau B, Phase 3)
soit diffus plutot que concentre sur un numero precis est une information utile pour la Phase 5 :
si une instabilite temporelle existe, elle ne sera probablement pas attribuable a un seul numero du
complementaire. Le §20 du Cahier (biais de position) est NON TESTABLE avec ces donnees (source pre-triee).
Limitations : correction multiple appliquee par famille, pas globalement sur le projet (prevu Phase 14) ;
3 lignes non triees (dont les 2 derniers tirages du fichier) notees pour la Phase 12, non exploitables
statistiquement (n=3).
Explication alternative envisagée : le tri des colonnes vient tres probablement de la source (affichage
usuel des resultats de loterie, cf. RESEARCH_REVIEW.md) plutot que d'un choix de l'utilisateur lors de
sa reparation du fichier - a confirmer si possible, sans consequence sur la suite du projet.
Fichiers produits : reports/ANOMALY_REPORT.md (avec section de retractation), scripts/phase4_anomalies.py,
scripts/diagnostic_position_order.py, research_audit.json (mis a jour), logs/run_phase4_*.json.
Décision : GO. Aucune anomalie niveau B/C a transmettre en l'etat. Passage a la Phase 5 (analyse
temporelle, H007) sur confirmation explicite de l'utilisateur.
