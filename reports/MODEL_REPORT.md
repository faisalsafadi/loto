# PHASE 9 — Baselines et modèles statistiques

STATUT : **NO-GO** (aucun modèle n'offre d'avantage prédictif exploitable — conclusion scientifique
valide, cf. précédent de la Phase 7)

## Ce qui a été testé

Trois modèles, dans l'ordre imposé (IMPLEMENTATION_SPEC §33) : `baseline_random` → `frequency_baseline`
→ `régression logistique`. Question : un modèle utilisant l'historique des tirages bat-il
significativement l'hypothèse d'équiprobabilité pure (6/49), sur un split temporel unique
train/test (pas le walk-forward complet — réservé à la Phase 10, seul test officiel de H008) ?

## Méthode

- **Split** : 80 % des tirages les plus anciens en train (id 1-2524, n=2524), 20 % les plus récents
  en test (id 2525-3155, n=631), coupé au niveau du tirage entier. Pré-enregistré avant exécution
  (amendement A9).
- **baseline_random** : p=6/49 constant, sans ajustement.
- **frequency_baseline** : fréquence cumulée de tout l'historique avant t, lissée avec un
  pseudo-compte α=10 ancré sur 6/49 (pré-enregistré, non ajusté sur les résultats).
- **régression logistique** : features `freq_last_{10,20,50,100,250}`, `gap_current` (sentinel -1
  remplacé par `chronological_id-1`), `prev_sum/prev_odd_count/prev_low_count/prev_overlap`.
  Hyperparamètres par défaut scikit-learn (C=1.0), aucune recherche d'hyperparamètre. Imputation et
  standardisation ajustées sur train uniquement.
- **Métrique primaire désignée à l'avance** : log loss par tirage (moyenne sur les 49 numéros d'un
  même tirage, puis comparaison au niveau du tirage — unité d'observation indépendante, cf.
  dépendance structurelle notée en Phase 8). Test : Wilcoxon signé-rang apparié. Famille de 3
  comparaisons pré-enregistrées, correction de Holm (aucune autre comparaison formelle n'a été
  menée — Brier, hits, calibration sont rapportés à titre descriptif uniquement).

## Résultats (chiffres)

| Modèle | Log loss | Brier | Hits/tirage moy. | P(numéro tiré) | P(numéro non tiré) |
|---|---|---|---|---|---|
| baseline_random | 0,371776 | 0,107455 | 0,7353 | 0,122449 | 0,122449 |
| frequency_baseline | 0,372097 | 0,107523 | 0,7242 | 0,122303 | 0,122469 |
| logistic_regression | 0,371880 | 0,107478 | 0,6894 | 0,122477 | 0,122564 |

Distribution des hits (nombre de numéros corrects parmi les 6 numéros de plus forte probabilité
prédite, sur 631 tirages de test) :
- random (= combinaison fixe {1..6}) : 0→284, 1→245, 2→88, 3→13, 4→1, 5→0, 6→0
- frequency : 0→269, 1→275, 2→80, 3→6, 4→1, 5→0, 6→0
- logistic : 0→300, 1→239, 2→80, 3→12, 4→0, 5→0, 6→0

**Comparaisons formelles (Wilcoxon apparié, log loss par tirage, n=631, correction Holm, α=0,05) :**

| Comparaison | Diff. moyenne | p brut | p ajusté (Holm) | H0 rejetée |
|---|---|---|---|---|
| frequency − random | **+0,000321** (frequency pire) | 0,002693 | 0,007550 | Oui |
| logistic − random | **+0,000104** (logistic pire) | 0,002517 | 0,007550 | Oui |
| logistic − frequency | −0,000217 (logistic meilleur) | 0,049714 | 0,049714 | Oui (à la limite) |

**Remarque de nomenclature statistique** : les comparaisons `frequency−random` et `logistic−random`
sont, de par la construction de `baseline_random` (log loss strictement constant sur les 631
tirages — voir justification mathématique ci-dessous), des tests à un échantillon sur la
distribution du modèle challenger, et non des comparaisons bivariées de deux séries variables.
Seule `logistic−frequency` est une comparaison appariée au sens plein. Le test de Wilcoxon reste
valide dans les deux cas ; c'est une précision d'interprétation, pas un vice de méthode.

**Coefficients de la régression logistique** (sur features standardisées) :
`freq_last_10`=-0,00978, `freq_last_20`=+0,01833, `freq_last_50`=-0,01842, `freq_last_100`=+0,00023,
`freq_last_250`=+0,00524, `gap_current_adjusted`=+0,00644, `prev_sum`=-0,0000748,
`prev_odd_count`=+0,0000328, `prev_low_count`=-0,0000436, `prev_overlap`=-0,000121 — tous d'ordre de
grandeur minuscule, aucun ne domine, cohérent avec l'absence de signal retenu en Phases 3-7.

**Calibration** (bins à largeur égale, fréquence observée vs probabilité moyenne prédite) :
- `baseline_random` : un seul bin (prédiction constante), fréquence observée = 0,122449, identique
  à 6/49 au 6ᵉ chiffre près — cohérent par construction.
- `frequency_baseline` : fréquence observée oscille entre 0,117 et 0,153 sans tendance monotone
  claire avec la probabilité prédite (qui croît de 0,112 à 0,139) — un modèle bien calibré et
  informatif montrerait une relation croissante nette ; ici la fréquence observée reste proche du
  taux de base (~0,122) quel que soit le bin.
- `logistic_regression` : même absence de relation croissante nette ; les deux bins extrêmes (plus
  fortes probabilités prédites) montrent une fréquence observée notablement plus basse (0,061 et
  0,043), mais sur des effectifs très faibles (n=33 et n=23 sur 30919 observations) — à traiter
  comme anecdotique, pas comme un signal anti-prédictif avéré.

## Interprétation

Les trois comparaisons sont statistiquement significatives après correction de Holm, mais dans le
sens opposé à ce que rechercherait une démonstration de prédictibilité : les deux modèles qui
exploitent l'historique font **moins bien** que l'hypothèse d'équiprobabilité pure sur la métrique
primaire. L'ampleur est négligeable (différence relative de log loss ≈0,03-0,09 %) : c'est la
signature attendue d'un modèle qui absorbe du bruit d'échantillonnage de la période d'entraînement
sans qu'aucun signal réel ne soit présent pour compenser cette variance ajoutée — pas une preuve
d'un quelconque « anti-pattern » exploitable.

Diagnostic complémentaire cohérent : pour `frequency_baseline` et `logistic_regression`, la
probabilité moyenne assignée aux numéros **effectivement tirés** est très légèrement **inférieure**
à celle assignée aux numéros non tirés (ex. frequency : 0,122303 vs 0,122469). Un modèle avec un
vrai pouvoir discriminant montrerait l'inverse. Cette inversion, bien que d'ampleur infime, est
cohérente avec l'absence totale de signal plutôt qu'avec un signal de sens opposé.

Ce résultat est pleinement cohérent avec les Phases 3 à 7 : aucune structure de fréquence
(H001/H004 rejetées), de paire/triplet (H005/H006 rejetées) n'a survécu à la correction des
comparaisons multiples en exploration. Un modèle entraîné sur ce même historique ne peut pas
produire, hors-échantillon, un avantage qui n'existe pas dans les données qui l'alimentent.

## Limitations

- **Split unique, pas walk-forward** : ce résultat est un dépistage préliminaire. Il NE CONSTITUE
  PAS le test officiel de H008 (réservé à la Phase 10, IMPLEMENTATION_SPEC §35). H008 reste
  **UNTESTED**.
- α=10 (frequency_baseline) et C=1,0 (logistique) sont des choix pré-enregistrés, non validés par
  une recherche d'hyperparamètre. Une autre valeur pourrait donner un résultat marginalement
  différent — mais toute exploration de cet espace devrait passer par un walk-forward/TimeSeriesSplit
  en Phase 10, jamais par un ajustement a posteriori sur ce résultat (IMPLEMENTATION_SPEC §34).
- Les bins de calibration extrêmes pour la régression logistique reposent sur de très petits
  effectifs (n=33, n=23) : la baisse de fréquence observée y est rapportée mais ne doit pas être
  interprétée comme un signal fiable.
- Famille de comparaisons formelles limitée à 3 tests pré-enregistrés sur le log loss ; Brier,
  hits-rate et calibration sont descriptifs uniquement, aucun test formel supplémentaire n'a été
  mené dessus (pas de comparaisons multiples cachées).

## Explication alternative envisagée

Deux pistes, explicitement écartées comme justification pour agir maintenant :
1. *Le split train/test capture-t-il un changement de régime entre les deux périodes ?* Peu
   probable : H007 (stabilité temporelle) a été rejetée en Phase 5 (p=0,741 principaux, p=0,542
   complémentaire) — aucune rupture structurelle détectée qui expliquerait une dégradation
   spécifique à la période de test.
2. *Un autre choix d'hyperparamètre (α, C) inverserait-il le résultat ?* Possible mais non
   exploré ici par construction (pré-enregistrement) : l'explorer maintenant, après avoir vu ce
   résultat, serait du p-hacking. Si cette piste doit être suivie, elle doit l'être via
   TimeSeriesSplit dans le cadre de la Phase 10, jamais en ajustant ce script a posteriori.

## Fichiers produits

- `reports/model_summary_phase9.json`
- `reports/calibration_{random,frequency,logistic}.csv`
- `src/loto_research/models/baselines.py`, `metrics.py`, `logistic.py`, `evaluate.py`
- `scripts/phase9_models.py`
- `tests/test_models.py`
- `logs/run_phase9_*.json`

## Décision

**NO-GO** sur la question « un modèle bat-il significativement et utilement les baselines » :
la régression logistique ne justifie pas l'ajout de modèles plus complexes (Random Forest,
Gradient Boosting, XGBoost) à ce stade (IMPLEMENTATION_SPEC §33 : « aucun modèle complexe n'est
ajouté sans que le précédent ait justifié l'expérience »). La chaîne d'escalade de complexité
s'arrête ici pour cette itération.

Ceci **ne clôt pas H008**. Le test officiel reste la Phase 10 (walk-forward complet), qui devra
évaluer `baseline_random`, `frequency_baseline` et `logistic_regression` — pas de modèles plus
complexes, faute de justification empirique — sur des fenêtres glissantes réentraînées, seule
preuve acceptable de valeur prédictive (Cahier §2, Niveau D).
