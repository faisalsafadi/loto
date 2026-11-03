# PHASE 10 — Backtesting walk-forward (TEST OFFICIEL DE H008)

STATUT : **NO-GO** — aucun pouvoir prédictif mesurable détecté (résultat scientifique légitime,
attendu par défaut, Cahier §26)

## Ce qui a été testé

H008 (hypothèse centrale du projet) : « Aucun modèle (fréquentiste, Markov, ML) n'améliore
significativement les performances hors-échantillon par rapport à baseline_random et
frequency_baseline. » Ceci est le **seul test officiel acceptable** de valeur prédictive
(Niveau D, Cahier §2) — contrairement au dépistage préliminaire de la Phase 9 (split unique,
n=631), ce walk-forward évalue **2655 points de prédiction indépendants**, chacun strictement
hors-échantillon par construction.

## Méthode

- **Fenêtre EXPANDING**, entraînement minimal de 500 tirages, évaluation sur les tirages
  501 à 3155 (2655 points de prédiction). Choix pré-enregistrés avant exécution (amendement A10).
- `baseline_random` et `frequency_baseline` : formules nativement causales/expanding (vérifiées
  en Phase 8-9), évaluées directement sur toute la plage.
- `logistic_regression` : réentraînée tous les 10 tirages (266 réentraînements), prédictions
  gelées entre deux réentraînements — jamais de donnée du futur dans un entraînement.
- **Spot-check de non-fuite** : `test_no_future_features()` sur 20 points de contrôle répartis sur
  le walk-forward (20/20 passés, 0 échec) — propriété du code validée, pas seulement au moment de
  la construction initiale du dataset en Phase 8.
- **Test primaire désigné à l'avance** : log loss par tirage, Wilcoxon signé-rang apparié + IC
  bootstrap (2000 réplications, percentile, rééchantillonnage par tirage). 3 comparaisons
  pré-enregistrées, correction de Holm — famille propre à cette phase (non combinée avec celle de
  la Phase 9).
- Aucun modèle plus complexe que la régression logistique testé : la Phase 9 n'a pas justifié
  Random Forest / Gradient Boosting / XGBoost (IMPLEMENTATION_SPEC §33).

## Résultats (chiffres)

| Modèle | Log loss | Brier | Hits/tirage moy. | P(numéro tiré) | P(numéro non tiré) |
|---|---|---|---|---|---|
| baseline_random | 0,371776 | 0,107455 | 0,7424 | 0,122449 | 0,122449 |
| frequency_baseline | 0,372142 | 0,107533 | 0,7277 | 0,122352 | 0,122463 |
| logistic_regression | 0,371833 | 0,107468 | 0,7096 | 0,122530 | 0,122550 |

**Comparaisons formelles OFFICIELLES (H008)** — Wilcoxon apparié, log loss par tirage, n=2655,
correction de Holm (α=0,05) :

| Comparaison | Diff. moyenne | IC95% bootstrap | p brut | p ajusté (Holm) | H0 rejetée |
|---|---|---|---|---|---|
| frequency − random | **+0,000366** (frequency pire) | [+0,000238, +0,000487] | 5,3×10⁻⁶ | 1,6×10⁻⁵ | Oui |
| logistic − random | **+0,000057** (logistic pire) | [+0,000008, +0,000103] | 0,00717 | 0,00717 | Oui |
| logistic − frequency | −0,000309 (logistic meilleur) | [−0,000443, −0,000172] | 0,00084 | 0,00168 | Oui |

Les trois intervalles de confiance excluent 0 : ce n'est plus une tendance fragile comme en
Phase 9, c'est une conclusion robuste sur 2655 tirages indépendants.

**Vérification arithmétique de cohérence** : (frequency−random) − (logistic−random) =
0,000366 − 0,000057 = 0,000309 = −(logistic−frequency), aux arrondis près. Les trois estimations
sont internement cohérentes.

**Ampleur relative** (par rapport au log loss de `baseline_random`) :
- frequency_baseline : **0,098 % plus mauvais**
- logistic_regression : **0,015 % plus mauvais** (environ 6 fois moins dégradé que frequency)
- Sanity check sur `baseline_random` : le log loss est strictement identique à celui calculé en
  Phase 9 (0,371776...) au chiffre près — attendu, puisque cette quantité est une constante
  mathématique indépendante des données (cf. Phase 9), pas une coïncidence.

**Calibration** (fréquence observée vs probabilité moyenne prédite, 10 bins) :
- `baseline_random` : un seul bin (prédiction constante 6/49), fréquence observée = 0,122449 —
  identique à 6/49 au 7ᵉ chiffre près sur 130 095 observations. Confirmation directe qu'aucune
  dérive du taux de base réel n'existe sur la période de test.
- `frequency_baseline` : la fréquence observée **décroît** dans les bins de plus forte probabilité
  prédite (bin6→9 : 0,1244 → 0,1109 → 0,0977 → 0,0930, pour des effectifs n=12148, 1777, 174, 86),
  alors qu'un modèle informatif montrerait l'inverse. C'est la signature directe d'un biais de
  sur-confiance : les numéros jugés « les plus probables » sur la base de leur fréquence historique
  sont en réalité légèrement MOINS susceptibles d'être tirés par la suite — cohérent avec
  l'absence de persistance réelle (H004 rejetée en Phase 6), pas avec un signal exploitable de
  sens inverse.
- `logistic_regression` : calibration nettement plus proche de la diagonale dans la masse
  principale des observations (bins 2 à 6, soit ≈98,4 % des 130 095 observations : prédit
  0,1194→observé 0,1212 ; prédit 0,1230→observé 0,1231 ; prédit 0,1273→observé 0,1182 ; etc.).
  Les divergences n'apparaissent que dans les bins extrêmes à très faible effectif (n=56, 54, 32,
  10) — à traiter comme bruit d'échantillonnage, pas comme signal.

## Interprétation

**H008 est tranchée : son hypothèse alternative (H1 — un modèle améliore les performances) est
rejetée.** Non seulement aucun modèle ne bat `baseline_random`, mais les deux modèles testés font
**significativement moins bien**, avec des intervalles de confiance excluant 0 sur 2655 tirages
indépendants. C'est une confirmation plus forte de H000 que la simple absence de différence : les
modèles qui exploitent l'historique introduisent une dégradation mesurable, quoique d'ampleur
infime (0,015 % à 0,098 % de log loss).

La calibration explique *pourquoi* la hiérarchie observée (random > logistic > frequency) est
cohérente et non accidentelle : `frequency_baseline` traduit directement la fréquence historique
brute en probabilité, et hérite donc pleinement du bruit d'échantillonnage de l'historique — y
compris dans sa queue de distribution, où elle est la plus confiante et la plus fausse.
`logistic_regression`, via sa régularisation L2, resserre ses prédictions vers une plage beaucoup
plus étroite (0,110–0,153 contre 0,095–0,155 pour frequency) et se rapproche ainsi de l'uniformité
— ce qui réduit mécaniquement l'essentiel du bruit injecté, sans toutefois l'éliminer complètement.
Un modèle qui ferait disparaître totalement ce bruit convergerait vers `baseline_random` lui-même.

Ce résultat clôt la chaîne d'hypothèses H001 à H008 sur une conclusion cohérente de bout en bout :
aucune structure de fréquence, de gap, de paire, de triplet, ni de stabilité temporelle n'a résisté
à la correction des comparaisons multiples en exploration (Phases 3 à 7) ; aucun modèle entraîné
sur ces mêmes données ne peut donc produire, hors-échantillon, un avantage qui n'existe pas dans
les données qui l'alimentent.

**Conséquence directe pour H008-b** (numéros à probabilité prédite la plus basse) : la sortie
officielle pré-enregistrée s'applique telle que spécifiée dans HYPOTHESES.md — « sous H0, tous les
numéros sont statistiquement équiprobables ; aucun numéro ne présente de risque supérieur ou
inférieur significatif à un autre. » Aucune liste de numéros favorisés ou déconseillés n'est
produite ni ne sera produite sur la base de ces résultats.

## Limitations

- Seuls trois modèles ont été testés (`baseline_random`, `frequency_baseline`,
  `logistic_regression`) — pas de Random Forest, Gradient Boosting, XGBoost ni réseau de neurones,
  faute de justification empirique en Phase 9 (IMPLEMENTATION_SPEC §33). Ce résultat ne peut pas
  être extrapolé littéralement à tout modèle imaginable non testé ; il peut l'être raisonnablement
  compte tenu de la cohérence totale des Phases 1 à 10 (aucune structure exploitable identifiée à
  aucun niveau d'analyse).
- `α=10` et `C=1,0` restent des choix pré-enregistrés non optimisés. Le réentraînement de la
  régression logistique tous les 10 tirages (pas tous les tirages) est un compromis de coût
  assumé, documenté en amendement A10 — pas une recherche d'hyperparamètre déguisée.
- Les bins de calibration extrêmes (n<100) ne sont pas fiables individuellement ; seule leur
  tendance cohérente sur plusieurs bins consécutifs (frequency_baseline, bins 6-9) est interprétée.

## Explication alternative envisagée

*Le walk-forward capture-t-il un artefact du découpage (ex. minimum d'entraînement trop court au
début) ?* Peu probable : les 2655 points de prédiction couvrent une plage très large (tirages
501 à 3155, soit l'essentiel de l'historique), et H007 (stabilité temporelle, Phase 5) n'a détecté
aucune rupture qui concentrerait artificiellement la dégradation sur une sous-période. Le résultat
est cohérent avec le dépistage préliminaire de la Phase 9 sur une fenêtre totalement différente
(les 20 % les plus récents) — deux échantillons disjoints pointent dans la même direction.

## Fichiers produits

- `reports/walk_forward_summary_phase10.json`
- `reports/calibration_walkforward_{random,frequency,logistic}.csv`
- `src/loto_research/backtesting/walk_forward.py`
- `src/loto_research/models/metrics.py` (mis à jour : `bootstrap_mean_diff_ci`)
- `scripts/phase10_walk_forward.py`
- `tests/test_walk_forward.py`, `test_metrics_bootstrap.py`
- `logs/run_phase10_*.json`

## Décision

**NO-GO.** H008 est résolue : aucun pouvoir prédictif mesurable n'est détecté ; au contraire, les
modèles testés font significativement moins bien que l'hypothèse d'équiprobabilité pure, avec des
intervalles de confiance excluant 0 sur 2655 tirages indépendants hors-échantillon. C'est un
résultat scientifique valide et attendu par défaut (H000), pas un échec de méthode.

**H008 et H008-b passent du statut UNTESTED à REJECTED** (l'hypothèse alternative — un avantage
prédictif existe — est rejetée ; H0 est confirmée hors-échantillon). Mise à jour de HYPOTHESES.md
ci-dessous.

---

## ERRATUM (2026-10-08) — correction d'une affirmation inexacte

Dans la section « Explication alternative envisagée » ci-dessus, le rapport affirme que la
cohérence avec la Phase 9 vient de « deux échantillons disjoints ». **C'est inexact.** La fenêtre
de test de la Phase 9 (tirages 2525 à 3155) est entièrement incluse dans la plage d'évaluation de la
Phase 10 (tirages 501 à 3155). Les deux résultats ne sont donc pas indépendants : la Phase 9
n'est pas une réplication de la Phase 10, et le niveau REPLICATED n'est pas attribué.

Ce qui reste valable : la conclusion de la Phase 10 repose sur son propre test (2655 tirages,
Wilcoxon apparié, correction de Holm, IC bootstrap) et n'est pas modifiée. La phrase originale est
conservée plus haut pour traçabilité, conformément à la règle du projet (une rétractation est
documentée, jamais effacée).