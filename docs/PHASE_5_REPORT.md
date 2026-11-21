### Phase 5 — Analyse temporelle
STATUT : GO

Ce qui a été testé : H003 (dependance entre tirages consecutifs, permutation, amendements A2/A3/A5) ;
H007 (stabilite inter-periodes, chi2 d'homogeneite, amendement A3), principaux et complementaire
separement ; runs test sur la parite de la somme (exploratoire, A2).
Méthode : scripts/phase5_temporal.py. Essai chronometre (2000 perm., 1.3s) puis run officiel
(20000 perm., seed 42, 12.8s). 10 tests unitaires passes avant execution. Incident d'environnement
(symlink python3 casse par une mise a jour systeme) resolu avant execution, sans impact sur les
resultats (voir docs/AMENDMENTS.md).
Résultats (chiffres) :
- H003 : 3124/3154 paires chronologiques reellement consecutives (30 exclues, A5). Moyenne observee
  de numeros communs = 0.7125 (theorique sous independance = 0.7347). p_permutation = 0.94615.
- H007 principaux : chi2=178.99, df=192, p=0.7406.
- H007 complementaire : chi2=189.29, df=192, p=0.5418.
- Runs test (parite somme) : n_runs=1558 (attendu 1578.45), z=-0.728, p=0.4663.
Interprétation : aucune dependance temporelle detectee (H003 rejetee). Aucune instabilite inter-periodes
detectee, ni pour les principaux ni pour le complementaire (H007 rejetee dans les deux cas). Le signal
Niveau B du complementaire (Phase 3, p=0.0235) n'est corrobore ni par une localisation sur un numero
(Phase 4) ni par une instabilite temporelle (ici) : il est desormais traite comme compatible avec du
bruit d'echantillonnage plutot que comme une anomalie necessitant une investigation plus poussee.
Limitations : H007 teste l'homogeneite globale, pas une rupture datee (CUSUM/ruptures resterait a faire
si H007 avait rejete H0, ce qui n'est pas le cas ici) ; H003 exclut structurellement les paires
chevauchant un tirage absent.
Explication alternative envisagée : sans objet (aucun resultat significatif a expliquer ici).
Fichiers produits : reports/TEMPORAL_REPORT.md, logs/run_phase5_*.json, research_audit.json (mis a jour).
Décision : GO. Aucune anomalie temporelle retenue. H000 (absence de structure exploitable) continue
d'etre l'hypothese la mieux soutenue par l'ensemble des Phases 3 a 5. Passage a la Phase 6 (Monte-Carlo
general), Phase 7 (paires/triplets) ou Phase 8 (features) sur confirmation explicite de l'utilisateur.
