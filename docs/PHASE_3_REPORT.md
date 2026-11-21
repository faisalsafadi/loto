### Phase 3 — Analyse statistique fondamentale
STATUT : GO

Ce qui a été testé : H001 (uniformite des 6 principaux, Monte-Carlo, amendement A1), H002 (uniformite
du complementaire, chi2(48), amendement A7), distribution des sommes, pair/impair, bas/haut (distributions
exactes par denombrement/hypergeometrique).
Méthode : scripts/phase3_statistics.py. Essai chronometre (2000 sim., 2.1s) puis run officiel
(100000 sim., seed 42, 104.7s). 17 tests unitaires passes avant execution.
Résultats (chiffres) :
- H001 : chi2 naif(df=48)=32.28 p=0.9602 (indicatif) ; Monte-Carlo p=0.89854, E_null=43.04 (proche de
  43 theorique, confirme le calibrage de l'amendement A1, coherent avec l'essai a 2000 sim. E_null=42.93).
- H002 : chi2(48)=69.355, p=0.0235 (test PRIMAIRE unique, pre-enregistre sans correction).
- Somme : chi2=202.98, df=184, p=0.1607 (vs distribution exacte par denombrement).
- Pair/impair : chi2=10.782, df=6, p=0.0954 (vs hypergeometrique exacte).
- Bas/haut : chi2=5.899, df=6, p=0.4346 (vs hypergeometrique exacte).
Interprétation : H001 ne montre aucune preuve de structure (H0 non rejetee). H002 franchit son seuil
pre-enregistre (p=0.0235<0.05) mais reste Niveau B (anomalie statistique brute, Cahier §2) : un p-value
isole ne suffit jamais a etablir un Niveau C. Ce resultat est proche de celui rapporte par l'outil externe
non audite (a_lire, chi2=69.36, p=0.02348) - coherence attendue (meme calcul standard, memes donnees),
mais AUCUNE investigation temporelle sur une fenetre choisie a posteriori (2015-2019) n'est menee ici :
toute analyse temporelle de H002 utilisera exclusivement le decoupage pre-enregistre (amendement A3).
Aucun autre test ne montre de deviation.
Limitations : variance des z-scores descriptifs marginale (ne capture pas les correlations du tirage
sans remise) ; ~33 tirages absents non inclus (A5) ; H002 non corrigee pour comparaisons multiples au-dela
de son propre protocole (correction globale du projet prevue en synthese finale, Phase 14).
Explication alternative envisagée : le signal H002 pourrait etre pur hasard (1 test sur 5 rapportes ici
sous H0 franchit 0.05 avec une probabilite non negligeable ~1-(0.95)^5=22%) ; investigation ulterieure
necessaire, pas de conclusion a ce stade.
Fichiers produits : reports/STATISTICAL_REPORT.md, logs/run_phase3_*.json.
Décision : GO. H002 transmise comme candidate Niveau B a la Phase 4 (recherche d'anomalies, avec
correction multiple formelle) et a la Phase 5 (H007, stabilite temporelle, decoupage A3 uniquement).
