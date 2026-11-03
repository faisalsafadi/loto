# EXECUTION_PLAN.md

## LOTO MAROC RESEARCH ENGINE
### Plan d'orchestration — exécution séquentielle contrôlée

Version : 1.0
Statut : ACTIF
Documents de référence : `Cahier des charges` v1.0, `IMPLEMENTATION_SPEC.md` v1.0

---

## 0. Principe de fonctionnement de ce document

Ce document est le **chef d'orchestre** du projet. Il ne remplace ni le
Cahier des charges (le "quoi" et le "pourquoi") ni l'IMPLEMENTATION_SPEC.md
(le "comment technique"). Il définit **l'ordre**, **les critères d'arrêt**,
et **les conditions de passage** entre les étapes.

Règles de fonctionnement non négociables :

1. **Une seule phase à la fois.** Claude ne commence jamais la phase N+1
   avant que la phase N soit officiellement clôturée par un statut GO.
2. **Chaque phase produit obligatoirement** : du code, des tests, des
   résultats bruts, un rapport court, et une décision explicite.
3. **Chaque phase se termine par un verdict** : `GO`, `NO-GO`, ou `BLOCKED`.
   - `GO` → la phase suivante peut démarrer.
   - `NO-GO` → un problème de fond a été détecté (données invalides,
     hypothèse infirmée, leakage détecté...) ; il faut corriger avant de
     continuer, ou accepter formellement la conclusion négative.
   - `BLOCKED` → il manque une information, une décision utilisateur, ou
     une ressource ; Claude doit dire précisément quoi.
4. **Aucun résultat postérieur ne contamine une décision antérieure.**
   Toute réévaluation avec des données plus récentes doit être marquée
   `REANALYSIS` et ne remplace jamais la conclusion originale dans le
   journal.
5. **Claude a le droit et le devoir de conclure négativement** à toute
   étape ("aucune structure exploitable détectée", "hypothèse rejetée",
   "aucun pouvoir prédictif mesurable"). Ce n'est pas un échec du projet,
   c'est un résultat scientifique valide.
6. **L'utilisateur valide chaque transition.** Après le verdict d'une
   phase, Claude s'arrête et attend une confirmation explicite avant de
   passer à la phase suivante — même en cas de `GO`.

Chaque phase suit le même gabarit de sortie :

```
### Phase X — <nom>
STATUT : GO | NO-GO | BLOCKED

Ce qui a été testé :
Méthode :
Résultats (chiffres) :
Interprétation :
Limitations :
Explication alternative envisagée :
Fichiers produits :
Décision :
```

---

## 1. Vue d'ensemble des phases

| Phase | Nom | Sortie principale | Dépend de |
|---|---|---|---|
| 0 | Initialisation du projet | Structure, environnement, manifest | — |
| 1 | Import et contrôle des 3 159 tirages | RAW figé + SHA256 | 0 |
| 2 | Validation / nettoyage | ANALYTIC + logs de nettoyage | 1 |
| 3 | Analyse statistique fondamentale | Fréquences, χ², IC | 2 |
| 4 | Recherche d'anomalies | Anomalies classées A/B/C | 3 |
| 5 | Analyse temporelle | Autocorrélation, runs, régimes | 3 |
| 6 | Monte-Carlo | Distributions nulles simulées | 3 |
| 7 | Recherche de structures/patterns | Paires/triplets corrigés (FDR) | 4, 5, 6 |
| 8 | Construction des features | Dataset supervisé sans leakage | 2, 7 |
| 9 | Modèles statistiques et ML | Modèles entraînés + comparés au hasard | 8 |
| 10 | Backtesting walk-forward | Performance hors-échantillon | 9 |
| 11 | Système de prédiction prospective | Prédictions figées horodatées | 10 |
| 12 | Intégration des nouveaux tirages | Pipeline de mise à jour continue | 11 |
| 13 | IA locale spécialisée | Couche d'interprétation, pas de décision numérique | 10, 11 |
| 14 | Système de recherche continue | Boucle complète automatisée | 12, 13 |

Ordre d'exécution strict : **0 → 1 → 2 → 3 → (4, 5, 6 peuvent être menées
en parallèle conceptuellement mais rapportées séparément) → 7 → 8 → 9 →
10 → 11 → 12 → 13 → 14.**

Interdiction explicite : sauter à la phase 9 (ML) ou 11 (prédiction) sans
avoir clôturé 1 à 8 avec un verdict GO ou un NO-GO assumé et documenté.

---

## Phase 0 — Initialisation du projet

**Objectif** : mettre en place la structure logicielle, l'environnement,
et les garde-fous méthodologiques avant de toucher aux données.

**Actions** :
- Créer l'arborescence définie dans `IMPLEMENTATION_SPEC.md` §3.
- Créer `pyproject.toml` et verrouiller les dépendances (§68).
- Créer `configs/default.yaml` (§67).
- Initialiser le dépôt Git, premier commit.
- Créer `HYPOTHESES.md` (vide, prêt à recevoir des entrées horodatées).
- Créer `experiments/registry.csv` (vide, avec en-têtes).
- Créer `research_audit.json` (vide, structure initiale).

**Critères GO** :
- Arborescence conforme.
- `python --version` >= 3.12 confirmé.
- Dépendances installées et verrouillées.
- Premier commit Git enregistré (hash consigné).

**Verdict attendu** : GO / NO-GO / BLOCKED + hash du commit.

---

## Phase 1 — Import et contrôle des 3 159 tirages

**Objectif** : importer le fichier source sans jamais le modifier, et
produire un RAW figé et vérifiable.

**Actions** :
- Copier le fichier original dans `data/raw/` sans transformation.
- Calculer le SHA256, créer `data/raw/MANIFEST.json`.
- Charger les données et vérifier le nombre de lignes annoncé (3 159)
  contre le nombre de lignes réellement présentes.
- Aucune correction, aucune suppression à ce stade.

**Critères GO** :
- Fichier RAW intact, hash calculé et journalisé.
- Nombre de lignes constaté explicitement comparé au nombre attendu
  (3 159), écart signalé si présent.

**Vérifications obligatoires avant de continuer** :
- Le nombre annoncé (3 159) est-il confirmé par le fichier réel ? Si
  non → `NO-GO` ou `BLOCKED` selon la cause, jamais d'ajustement silencieux.

**Verdict attendu** : GO / NO-GO / BLOCKED.

---

## Phase 2 — Validation / nettoyage

**Objectif** : appliquer les règles de validation (§8 IMPLEMENTATION_SPEC,
règles V001–V007) et produire le dataset ANALYTIC.

**Actions** :
- Exécuter chaque règle de validation individuellement, avec compte
  d'échecs par règle.
- Exporter `invalid_records.csv` (aucune suppression silencieuse).
- Appliquer la règle date dupliquée → `keep first`, exporter
  `duplicate_dates.csv` / `removed_duplicate_dates.csv`.
- Exclure explicitement la ligne "0 0 0 0 0 0 + 0" → `invalid_records.csv`.
- Déterminer la règle du complémentaire (chevauchement ou non avec les
  6 principaux) à partir des règles officielles du jeu, **sans supposer**.
- Générer `DATA_QUALITY_REPORT.md` complet (§9 Cahier des charges).
- Créer `draw_id` (hash), `chronological_id`.
- Geler `data/analytic/draws.parquet` en tant que `DATASET_v001`.

**Critères GO** :
- Tous les enregistrements invalides sont documentés, aucun n'est perdu
  silencieusement.
- `DATA_QUALITY_REPORT.md` produit avec tous les indicateurs demandés.
- `dataset_manifest.json` créé.

**Verdict attendu** : GO / NO-GO / BLOCKED, avec le nombre final de
tirages valides utilisés pour la suite.

---

## Phase 3 — Analyse statistique fondamentale

**Objectif** : caractériser statistiquement le système sous l'hypothèse
nulle d'équiprobabilité, sans présumer d'anomalie.

**Actions** :
- Fréquences, fréquences annuelles/mensuelles, écarts à l'espérance,
  IC, z-scores pour les 49 numéros et le complémentaire.
- Test χ² d'équirépartition (numéros principaux et complémentaire
  séparément, modèles propres).
- Distribution des sommes, pair/impair, bas/haut.
- Classer chaque résultat au niveau A (observation) ou B (anomalie
  statistique brute, avant correction multiple).

**Critères GO** :
- `STATISTICAL_REPORT.md` produit, séparant clairement OBSERVATION /
  CALCUL / INTERPRÉTATION / LIMITATION.
- Aucun numéro n'est qualifié de "chaud" ou "froid" avec implication
  prédictive à ce stade.

**Verdict attendu** : GO / NO-GO / BLOCKED.

---

## Phase 4 — Recherche d'anomalies

**Objectif** : rechercher des anomalies (fréquence, position, dépendance)
en appliquant strictement les corrections de comparaisons multiples.

**Actions** :
- Appliquer Bonferroni, Holm, FDR/BH selon le nombre de tests.
- Journaliser systématiquement `number_of_tests`, `raw_p_value`,
  `adjusted_p_value`, `method`.
- Rechercher des anomalies mécaniques potentielles (biais de boules,
  positions) en signalant explicitement l'absence d'information physique
  sur les machines.
- Classer chaque anomalie détectée : niveau A/B/C selon les critères du
  Cahier des charges §2 (jamais niveau D à ce stade — le pouvoir
  prédictif n'est jugé qu'après validation hors-échantillon en phase 10).

**Critères GO** :
- `ANOMALY_REPORT.md` produit.
- Aucune anomalie n'est présentée sans sa p-value corrigée.
- Aucune conclusion de type "le système est truqué".

**Verdict attendu** : GO (avec liste des anomalies niveau B/C le cas
échéant) / NO-GO ("aucune anomalie détectée") / BLOCKED.

---

## Phase 5 — Analyse temporelle

**Objectif** : étudier la dépendance entre tirages successifs et
l'évolution des propriétés statistiques dans le temps.

**Actions** :
- Autocorrélation, runs test, répétitions (intersection entre tirages
  consécutifs), distance entre numéros, amplitudes.
- Découpage en périodes (2001–2005, 2006–2010, 2011–2015, 2016–2020,
  2021–2026) et comparaison des propriétés statistiques entre périodes.
- Détection de rupture (CUSUM, Bayesian change-point, `ruptures`) —
  toute rupture détectée doit être testée contre des explications
  alternatives (calendrier, règles, matériel, fréquence des tirages)
  avant toute autre interprétation.

**Critères GO** :
- `TEMPORAL_REPORT.md` produit.
- Toute rupture statistique est explicitement qualifiée comme
  "différence de propriétés statistiques entre périodes", jamais comme
  preuve de fraude.

**Verdict attendu** : GO / NO-GO / BLOCKED.

---

## Phase 6 — Monte-Carlo

**Objectif** : construire les distributions nulles de référence pour
comparer les statistiques observées à ce que produirait un système
purement aléatoire.

**Actions** :
- Simuler N tirages sous H0 (10 000 → 1 000 000 selon coût), seed
  enregistré (`numpy.random.Generator`).
- Comparer réel vs simulé pour : fréquences, gaps, paires, répétitions,
  sommes, statistiques complexes retenues en phases 3–5.
- Calculer les p-values empiriques avec correction appropriée.

**Critères GO** :
- `MONTE_CARLO.md` produit, seed documenté, reproductibilité vérifiée
  (relancer avec le même seed → mêmes résultats).

**Verdict attendu** : GO / NO-GO / BLOCKED.

---

## Phase 7 — Recherche de structures/patterns (paires, triplets)

**Objectif** : analyser les 1 176 paires et 18 424 triplets possibles
sans tomber dans le p-hacking.

**Actions** :
- Pipeline en quatre niveaux obligatoire : exploratoire → filtrage →
  validation → confirmation hors-échantillon.
- Correction FDR/BH systématique compte tenu du volume de tests.
- Aucun triplet/paire n'est présenté comme signal sur la seule base
  d'une p-value brute faible.
- Toute hypothèse née de l'observation des données est marquée
  `POST_HOC` dans `HYPOTHESES.md` et ne peut pas devenir confirmatoire
  rétroactivement.

**Critères GO** :
- `PAIRS.md` et `TRIPLETS.md` produits.
- `research_audit.json` mis à jour (nombre de fenêtres/seuils/modèles
  essayés, transparence totale).

**Verdict attendu** : GO (structures niveau C candidates, s'il y en a) /
NO-GO ("aucune structure exploitable détectée") / BLOCKED.

---

## Phase 8 — Construction des features

**Objectif** : construire le dataset supervisé (draw_date, number) →
target, en respectant strictement l'absence de data leakage.

**Actions** :
- Implémenter les features définies (§29 IMPLEMENTATION_SPEC) :
  fréquences glissantes, gap, fréquence de paires/triplets, statistiques
  de somme, etc.
- **Règle absolue** : toute feature au temps T doit être calculée
  uniquement avec des données < T.
- Implémenter et exécuter `test_no_future_features()`.
- Documenter les dépendances structurelles dues à la sélection de
  6 numéros par tirage (non-indépendance intra-tirage).

**Critères GO** :
- Test de non-leakage passé à 100 %.
- `FEATURES_v00X` versionné et documenté.

**Verdict attendu** : GO / NO-GO / BLOCKED — un échec du test de leakage
est un **NO-GO bloquant absolu**, aucune exception.

---

## Phase 9 — Modèles statistiques et ML

**Objectif** : entraîner et comparer les modèles dans l'ordre imposé,
chacun systématiquement comparé au hasard.

**Actions** :
- Ordre obligatoire : random baseline → frequency baseline → régression
  logistique → random forest → gradient boosting → XGBoost → LightGBM →
  réseau de neurones (uniquement si justifié).
- Aucun modèle complexe n'est ajouté sans que le précédent ait justifié
  l'expérience.
- Tuning uniquement via `TimeSeriesSplit` / walk-forward — jamais sur
  l'historique complet.

**Critères GO** :
- Chaque modèle comparé formellement à `baseline_random` et
  `frequency_baseline`.
- `MODEL_REPORT.md` produit avec toutes les métriques (log loss, Brier,
  calibration, top-k hit rate).

**Verdict attendu** : GO / NO-GO / BLOCKED.

---

## Phase 10 — Backtesting walk-forward

**Objectif** : mesurer la performance réelle hors-échantillon, seule
preuve acceptable de valeur prédictive (Niveau D).

**Actions** :
- Walk-forward strict : train < T, prédiction, observation réelle,
  ajout, nouveau train, nouvelle prédiction.
- Rolling window et expanding window.
- `test_no_future_features()` revérifié à chaque itération.
- Comparaison à `baseline_random` et `frequency_baseline` sur tout
  l'historique de backtest, pas seulement sur une fenêtre favorable.

**Critères GO** :
- `BACKTEST_REPORT.md` produit avec effect size, IC, p-value,
  p-value ajustée, performance hors-échantillon.
- Aucune sélection post-hoc de la "meilleure" fenêtre de test.

**Verdict attendu** :
- GO uniquement si une amélioration reproductible et statistiquement
  défendable est constatée hors-échantillon.
- NO-GO ("aucun pouvoir prédictif mesurable détecté") sinon — ceci est
  un résultat scientifique légitime et attendu comme hypothèse par
  défaut.

---

## Phase 11 — Système de prédiction prospective

**Objectif** : générer des prédictions figées, horodatées, avant chaque
tirage réel à venir — **uniquement si la phase 10 a produit un GO**.

**Actions** :
- Générer `prediction_YYYYMMDD.json` avec probabilité par numéro,
  niveau de confiance, incertitude, méthode, version modèle/dataset,
  seed.
- Calculer et conserver le SHA256 du fichier de prédiction.
- Interdiction absolue de modification rétroactive.

**Condition préalable stricte** : si la phase 10 a conclu `NO-GO`, la
phase 11 peut néanmoins produire des prédictions **à titre exploratoire
uniquement**, explicitement étiquetées comme non validées
statistiquement, jamais présentées comme fiables.

**Verdict attendu** : GO / NO-GO / BLOCKED.

---

## Phase 12 — Intégration des nouveaux tirages

**Objectif** : permettre l'ajout continu de nouveaux tirages sans
contaminer les prédictions passées.

**Actions** :
- Pipeline : validation → archivage → évaluation des prédictions
  précédentes (`RESULT_YYYY-MM-DD.json`, `EVALUATION_YYYY-MM-DD.json`)
  → ajout dataset → nouvelle version → recalcul features → réentraînement
  éventuel → nouvelle prédiction.
- Toute réanalyse rétroactive est marquée `REANALYSIS`.

**Critères GO** :
- Le nouveau tirage ne modifie aucune prédiction déjà figée.
- L'évaluation des prédictions passées est automatique et journalisée.

**Verdict attendu** : GO / NO-GO / BLOCKED.

---

## Phase 13 — IA locale spécialisée

**Objectif** : ajouter une couche d'interprétation qui n'invente jamais
de résultat numérique et ne se substitue jamais au moteur statistique.

**Actions** :
- L'IA reçoit les rapports (statistiques, modèles, backtest, anomalies)
  et produit hypothèses, questions de recherche, interprétations.
- Toute conclusion de l'IA doit être vérifiable par calcul indépendant.
- L'IA ne génère jamais directement de numéros.

**Critères GO** :
- Architecture conforme au schéma §44 (`IMPLEMENTATION_SPEC.md`) :
  le LLM n'est jamais la source primaire d'un résultat numérique.

**Verdict attendu** : GO / NO-GO / BLOCKED.

---

## Phase 14 — Système de recherche continue

**Objectif** : boucler l'ensemble (mise à jour, réévaluation, nouvelle
prédiction, rapport) en mode automatisable, avec les 4 modes définis
(`research`, `backtest`, `prediction`, `update`, `full`).

**Critères GO** :
- Reproductibilité totale démontrée : mêmes données + même code + même
  seed → mêmes résultats.
- `EXECUTIVE_SUMMARY.md` et `FINAL.md` produits, répondant explicitement
  aux 10 questions du §73 de `IMPLEMENTATION_SPEC.md`.

**Verdict attendu** : GO / NO-GO / BLOCKED.

---

## 2. Garde-fous transversaux (valables à toutes les phases)

- **Data leakage** : toute feature ou tout entraînement utilisant des
  données ≥ T pour prédire T est un `NO-GO` immédiat et bloquant.
- **Comparaisons multiples** : tout ensemble de tests > 1 doit
  enregistrer le nombre total de tests et appliquer une correction
  (Bonferroni / Holm / FDR selon le contexte) avant toute interprétation.
- **P-hacking** : toute expérience où plusieurs fenêtres, seuils ou
  modèles ont été essayés doit être journalisée dans
  `research_audit.json`, y compris les tentatives non retenues.
- **Overfitting** : toute performance en échantillon (in-sample) n'est
  jamais présentée comme une preuve de valeur prédictive — seule la
  performance hors-échantillon walk-forward compte.
- **Post-hoc vs confirmatoire** : toute hypothèse née de l'observation
  des données reste marquée `POST_HOC` / `EXPLORATORY` de façon
  permanente dans `HYPOTHESES.md`.
- **Non-rétroactivité** : aucune prédiction figée n'est jamais modifiée
  après coup ; toute réanalyse est marquée `REANALYSIS` et n'écrase rien.
- **Pas de conclusion de fraude** : quelle que soit l'anomalie détectée,
  la conclusion reste "anomalie statistique" ou "anomalie robuste
  nécessitant investigation complémentaire", jamais une accusation.

---

## 3. Prochaine étape

Ce document est prêt à guider l'exécution. Conformément à la règle de
fonctionnement (§0), la prochaine action attendue est le lancement de la
**Phase 0 — Initialisation du projet**, sur validation explicite de
l'utilisateur.
