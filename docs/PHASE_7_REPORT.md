### Phase 7 — Recherche de structures/patterns (paires, triplets)
STATUT : NO-GO ("aucune structure exploitable détectée")

Ce qui a été testé : H005 (1176 paires) et H006 (18424 triplets), tests binomiaux EXACTS (probabilite
constante par combinaison fixee, tirages independants - pas de Monte-Carlo necessaire, contrairement a
ce qu'anticipait HYPOTHESES.md avant verification), pipeline exploration (1577 tirages) / confirmation
hors-echantillon (1578 tirages), split chronologique pre-specifie avant tout calcul.
Méthode : scripts/phase7_pairs_triplets.py. 7 tests unitaires passes avant execution.
Résultats (chiffres) :
- Paires : 0/1176 candidats apres FDR-BH en exploration. Top brut : paire 11-41 (count=38, attendu
  20.11, ratio 1.89, p_brut=0.00028, p_ajuste=0.329).
- Triplets : 0/18424 candidats apres FDR-BH en exploration. Top brut : triplet 17-18-44 (count=9,
  attendu 1.71, ratio 5.26, p_brut=0.000074, p_ajuste=0.924).
- Aucun candidat n'a atteint l'etape de confirmation hors-echantillon (filtre a 0 des l'exploration).
Interprétation : NO-GO net, pas un cas limite (0 candidat sur ~19600 tests, pas "quelques-uns qui
echouent en confirmation"). Les valeurs extremes du top 10 (ratio x5, p<0.0001) restent statistiquement
banales compte tenu du volume de tests - exactement le piege que le pipeline est concu pour neutraliser.
Septieme test confirmatoire consecutif (H001,H003,H004,H005,H006,H007x2) sans structure detectee.
Limitations : split 50/50 chronologique pre-enregistre, non reconsidere ; niveaux filtrage/validation
du Cahier fusionnes en une seule confirmation hors-echantillon.
Explication alternative envisagée : sans objet (aucun resultat a expliquer).
Fichiers produits : reports/PAIRS.md, reports/TRIPLETS.md, reports/{pairs,triplets}_{exploration,
confirmation}.csv (tracabilite complete des ~19600+ tests), logs/run_phase7_*.json, research_audit.json.
Décision : NO-GO ("aucune structure exploitable détectée" au niveau combinatoire). Passage a la
Phase 8 (construction des features, sans data leakage) sur confirmation explicite de l'utilisateur.
