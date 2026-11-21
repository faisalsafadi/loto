# FINAL — LOTO MAROC Research Engine

Date de clôture : 2026-10-08
Dataset : DATASET_v001 (3155 tirages, 2001-03-17 → 2026-09-26) — Features : FEATURES_v001
Dernier commit de phase : 88cb93d (Phase 10)

## Conclusion

Sur l'historique analysé, **aucune structure statistique exploitable n'a été détectée et aucun
pouvoir prédictif n'a été mesuré**. L'hypothèse de base (H000 : tirage uniforme sans structure)
n'a été réfutée à aucun niveau d'analyse confirmatoire (deux signaux exploratoires non confirmés sur le
complémentaire, voir Q4). Ce résultat est négatif, légitime, et attendu par défaut
(Cahier §1, §40). Il a des limites précises, listées plus bas : il exclut des structures marquées,
pas des biais subtils.

## Réponses aux 10 questions (IMPLEMENTATION_SPEC §73)

Niveaux de conclusion : OBSERVED, STATISTICALLY_SIGNIFICANT, ROBUST, REPLICATED, PREDICTIVE
(Cahier §36). « Aucun » = aucun niveau atteint.

| # | Question | Réponse | Niveau |
|---|---|---|---|
| 1 | Les données sont-elles propres ? | Exploitables, avec trois réserves (voir Limites) : 3155 tirages au lieu de 3159 annoncés (−4, accepté), fichier source réparé avant import avec des modifications non documentées, ≈0,1 % des lignes dont les 6 numéros ne sont pas triés. Détail : DATA_QUALITY_REPORT.md | OBSERVED, sous réserves |
| 2 | Les numéros sont-ils compatibles avec l'uniformité ? | Oui. H001 : p Monte-Carlo = 0,899 (100 000 simulations, seed 42) ; 0/49 numéros significatifs après Holm | Aucun écart détecté |
| 3 | Le complémentaire présente-t-il une anomalie robuste ? | Non. Un seul résultat isolé de Niveau B : χ²(48) = 69,355, p brut = 0,0235 (H002). Non localisé (0/49 numéros après FDR-BH), non corroboré en Phases 4-5, compatible avec du bruit d'échantillonnage. Les deux signaux d'autocorrélation de la Q4 portent sur une propriété différente et ne le corroborent pas | STATISTICALLY_SIGNIFICANT (brut), pas ROBUST |
| 4 | Existe-t-il une dépendance temporelle ? | Aucune dépendance confirmatoire. H003 : p = 0,946 sur 3124 paires de tirages réellement consécutifs ; test des runs (parité) p = 0,466 ; CUSUM sur la somme p = 0,973. **Réserve** : autocorrélation lag-1 par numéro, test EXPLORATOIRE (non pré-enregistré), FDR-BH : 0/49 principaux, **2/49 valeurs du complémentaire significatives après correction**, non confirmées, inscrites comme H009 (POST_HOC). Détail : TEMPORAL_REPORT.md | Aucun niveau confirmatoire ; 2 signaux EXPLORATORY |
| 5 | Existe-t-il des ruptures ? | Aucune retenue. H007 : p = 0,741 (principaux), p = 0,542 (complémentaire) sur le découpage unique pré-enregistré. Le passage de 2 à 3 tirages par semaine (2015-2016) est une cause connue (A6). Une piste ruptures.Pelt sur le complémentaire (P(≥4 ruptures sous H0) = 0,045) a été fermée sans suite | Aucun |
| 6 | Existe-t-il des structures persistantes ? | Non. Paires : 0/1176 candidats après FDR-BH ; triplets : 0/18424 ; gaps : 0/49 (loi géométrique exacte). Aucun candidat n'a atteint l'étape de confirmation | Aucun |
| 7 | Les modèles ML améliorent-ils le hasard ? | Non. frequency_baseline : log loss +0,098 % (pire que le hasard) ; régression logistique : +0,015 % (pire aussi, mais moins que frequency). Seuls ces trois modèles ont été testés | Aucun |
| 8 | Cette amélioration survit-elle au backtesting ? | Sans objet : il n'y a pas d'amélioration. Le walk-forward (n = 2655, test officiel de H008) mesure à la place une dégradation significative : p ajustés Holm = 1,6×10⁻⁵ ; 0,0072 ; 0,0017, intervalles de confiance bootstrap excluant 0 | STATISTICALLY_SIGNIFICANT (dans le sens défavorable) |
| 9 | Est-elle stable dans le temps ? | Sans objet (pas d'amélioration). Aucune instabilité des propriétés statistiques n'a été détectée (H007). La dégradation mesurée porte sur 2655 tirages en expanding window | — |
| 10 | Existe-t-il une capacité prédictive mesurable ? | **Non.** Niveau D (Cahier §2) non atteint | Aucun |

## Statuts finaux des hypothèses

Convention du projet : REJECTED = l'hypothèse alternative (structure, anomalie, avantage) est
rejetée ; H0 n'est pas réfutée.

| Hypothèse | Statut | Résultat clé |
|---|---|---|
| H000 (cadre) | UNTESTED (non testable directement) | Aucune donnée ne la contredit |
| H001 | REJECTED | p MC = 0,899 |
| H002 | SUPPORTED, Niveau B, non corroboré | p brut = 0,0235 |
| H003 | REJECTED | p = 0,946 |
| H004 | REJECTED | 0/49 après FDR-BH |
| H005 | REJECTED | 0/1176 |
| H006 | REJECTED | 0/18424 |
| H007 | REJECTED | p = 0,741 / 0,542 |
| H008 | REJECTED | walk-forward n = 2655 |
| H008-b | REJECTED | sortie officielle : équiprobabilité, aucune liste de numéros |
| H009 (POST_HOC) | EXPLORATORY | 2/49 valeurs du complémentaire en autocorrélation lag-1 après FDR-BH, non confirmées, non confirmables sur DATASET_v001 |

## Limites : ce que ce résultat ne dit pas

1. **Absence de preuve n'est pas preuve d'absence.** Ordre de grandeur indicatif (calcul fait ici, approximation normale, pas une sortie du projet) : avec 3155 tirages, un test numéro par numéro corrigé pour 49 comparaisons ne détecte de façon fiable qu'un écart d'environ 16 à 20 % de la fréquence attendue pour un numéro isolé. Les biais plus fins ne sont pas exclus. Les tests globaux (χ², homogénéité) sont plus sensibles aux biais diffus, mais pas à n'importe quelle amplitude.
2. **Qualité de la source.** Le fichier a été réparé par l'utilisateur avant import, sans journal des modifications, et 4 tirages manquent par rapport au total annoncé. Aucune vérification croisée avec une source officielle n'a été faite. Une réparation qui aurait altéré des numéros ne serait pas détectable.
3. **Aucune information physique sur la machine** (RESEARCH_REVIEW §1.2). Une manipulation intermittente ou logicielle, comme l'affaire Tipton où les résultats paraissaient normaux, ne serait pas visible par ces tests. Ce projet ne conclut rien sur l'intégrité du tirage : il constate l'absence d'anomalie statistique détectable.
4. **Périmètre des modèles.** Seuls hasard, fréquence et régression logistique ont été testés. Random Forest, gradient boosting et réseaux de neurones ne l'ont pas été, faute de justification en Phase 9 (IMPLEMENTATION_SPEC §33). Hyperparamètres non optimisés par choix de pré-enregistrement. Fenêtre rolling non évaluée.
5. **Nature des comparaisons au hasard.** Le log loss de baseline_random est une constante mathématique ; les comparaisons contre lui sont des tests à un échantillon sur la distribution du modèle, et non des comparaisons de deux séries variables. Le test reste valide.
6. **Non exécuté** : Phases 11 à 14. PREDICTION_REPORT.md (Cahier §36) n'est pas produit : aucune prédiction prospective n'a été générée.

## Erratum sur BACKTEST_REPORT.md

Le rapport de Phase 10 contient une affirmation inexacte, corrigée dans un erratum ajouté en fin de
ce rapport. Il disait que la Phase 9 et la Phase 10 forment « deux échantillons disjoints ».
C'est faux : la fenêtre de test de la Phase 9 (tirages 2525 à 3155) est incluse dans celle de la
Phase 10 (501 à 3155). La cohérence des deux résultats n'est donc **pas** une réplication
indépendante, et le niveau REPLICATED n'est pas attribué. La conclusion de la Phase 10 repose sur
son propre test et reste inchangée.

## Implication pratique

Les données ne fournissent aucune base pour préférer un numéro ou une combinaison à un autre :
tous restent statistiquement équiprobables. Ce projet n'a pas analysé la structure des gains ni
les mises, donc il ne dit rien sur le rendement espéré d'un ticket. Les méthodes de réduction de
grilles (wheeling) ne portent pas sur la question étudiée ici.

## Livrables

reports/ : DATA_QUALITY_REPORT.md, STATISTICAL_REPORT.md, ANOMALY_REPORT.md, TEMPORAL_REPORT.md
(+ addendum), MONTE_CARLO.md, PAIRS.md, TRIPLETS.md, MODEL_REPORT.md, BACKTEST_REPORT.md,
EXECUTIVE_SUMMARY.md, FINAL.md. Journaux : HYPOTHESES.md, docs/AMENDMENTS.md (A1 à A10),
research_audit.json, experiments/registry.csv.

## Reproductibilité

- RAW : data/raw/loteriema_20260928_original.xlsx, SHA256
  eb5b5be17b050542b721cea1ad09e71ffc29b1dbfa92742647162c3d7eeb246b
- Seed : 42 (toutes les simulations et le bootstrap)
- Python 3.12.3, dépendances figées dans requirements.lock.txt
- Commits de phase : e6e487f (Phase 0) → 605c812 (Phase 1) → b0d8ec2 (Phase 2) → c9f407d (Phase 3)
  → 416a257 (Phase 4) → 401118d (Phase 5) → 3e5379e (Phase 6) → 495cb67 (Phase 7) → cd8fbe0 (Phase 8)
  → a213ee6 (Phase 9) → 88cb93d (Phase 10)
- Vérification : `python -m pytest tests/ -v`

## Addendum du 2026-10-31 — Sensibilité mesurée (banc d'essai M4)
La limite n°1 estimait à 16-20 % l'écart détectable par numéro (calcul à la main). Le banc M4
(reports/BENCHMARK_M4.md, 200 répétitions par cellule, seed 42) mesure à n = 3155 : puissance 16,5 % à +10 %,
75,5 % à +20 %, 99,5 % à +30 % ; biais minimal pour 80 % de puissance ≈ 22 % (interpolation grossière).
Le chiffre 16-20 % correspond donc à une puissance d'environ 50-75 %, pas à 80 %.
Autres sensibilités mesurées : un biais de paire n'est vu que via ses marginales (×3 pour ~87 % de puissance) ;
le test de paires de v1 (FDR, 1176) n'a pas été évalué par le banc ; une rupture localisée sur un numéro est
peu détectable (≤ 44 % à +30 % sur la seconde moitié ; test d'homogénéité entre moitiés analogue à H007 : 22 %) ;
le recouvrement consécutif (H003) détecte une reprise dès ρ = 0,02 (puissance 100 %, plus bas niveau testé).
Les conclusions de v1 ne changent pas : leur sensibilité est précisée.

Précision M4b (POST_HOC, 2026-10-31) : le recouvrement consécutif (H003) détecte une reprise de chaque numéro
du tirage précédent dès rho ≈ 0,009 avec 80 % de puissance à n = 3155 (11,5 % à 0,002 ; 40 % à 0,005 ; 92,5 % à 0,01),
ce qui précise la mention « dès rho = 0,02 » ci-dessus. Seule cette forme de dépendance est évaluée.

## Précision de provenance — 2026-11-01
L'utilisateur indique que les tirages proviennent du site officiel de la loterie (https://www.eloterie.ma/resultats).
Le fichier a ensuite été réparé à la main sans journal des modifications ; un recoupement systématique avec le site
n'est pas documenté. La provenance est donc connue, l'exactitude de chaque numéro n'est pas démontrée.
