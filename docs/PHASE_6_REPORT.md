### Phase 6 — Monte-Carlo
STATUT : GO

Ce qui a été testé : validation du moteur de simulation general (simulate_draws, reutilisable Phase 7) ;
H004 (distribution des gaps, 6 principaux) par loi geometrique EXACTE (pas de Monte-Carlo necessaire pour
le test lui-meme) ; extension exploratoire sur le complementaire.
Méthode : scripts/phase6_monte_carlo.py. Essai chronometre (500 hist., 0.5s) puis run officiel
(2000 hist. de calibration, seed 42, 2.1s). 9 tests unitaires passes avant execution.
Résultats (chiffres) :
- Reproductibilite du moteur : confirmee (meme seed -> resultats identiques).
- Calibration : 770822 gaps simules (numero 1, 2000 historiques) vs geometrique exacte p=6/49 :
  moyenne=8.146 (theorique 8.167), chi2=28.75 df=29 p=0.4782 -> moteur valide.
- H004 principaux : 0/49 numeros significatifs apres FDR-BH.
- Extension complementaire : 0/49 numeros significatifs apres FDR-BH.
Interprétation : le moteur Monte-Carlo general est operationnel et valide, pret pour la Phase 7.
H004 est rejetee : aucune structure dans la distribution des gaps, ni sur les principaux ni sur le
complementaire. Sixieme test consecutif (H001, H003, H004, H007 x2) a ne montrer aucune structure,
seul H002 garde un statut SUPPORTED degrade (Niveau B non corrobore, cf. Phase 5).
Limitations : gaps mesures en tirages du dataset, pas en jours civils (A5) ; aucune implication
predictive tiree d'un gap long (Cahier §14/18).
Fichiers produits : reports/MONTE_CARLO.md, logs/run_phase6_*.json, research_audit.json (mis a jour).
Décision : GO. Passage a la Phase 7 (paires/triplets) sur confirmation explicite de l'utilisateur -
c'est la phase la plus couteuse en tests du projet (1176 paires + 18424 triplets), le moteur Monte-Carlo
valide ici sera son infrastructure de reference.
