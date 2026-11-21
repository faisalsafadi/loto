# IMPLEMENTATION_SPEC.md

## LOTO MAROC RESEARCH ENGINE
### Spécification technique d'implémentation

Version: 1.0
Statut: ACTIVE
Type: Technical Implementation Specification

---

# 0. OBJECTIF

Ce document définit précisément l'implémentation technique du projet
LOTO MAROC RESEARCH ENGINE.

Le système doit transformer les données historiques du Loto Maroc en un
environnement reproductible de :

- validation des données ;
- statistiques ;
- simulation ;
- détection d'anomalies ;
- analyse temporelle ;
- recherche de ruptures ;
- génération de features ;
- machine learning ;
- backtesting ;
- prédiction prospective ;
- évaluation continue.

Le système doit être scientifique, reproductible et résistant au :

- data leakage ;
- overfitting ;
- p-hacking ;
- survivorship bias ;
- look-ahead bias ;
- sélection post-hoc des résultats ;
- comparaison multiple non corrigée.

---

# 1. STACK TECHNIQUE

## 1.1 Langage

Python >= 3.12

Version exacte utilisée par le projet :

```text
python --version


2. BIBLIOTHÈQUES
2.1 Data engineering

Utiliser :

pandas
numpy
openpyxl
pyarrow

Formats privilégiés :

CSV pour échange ;
Parquet pour datasets analytiques ;
XLSX uniquement comme source/import.
2.2 Statistiques

Utiliser :

scipy
statsmodels

Éventuellement :

pingouin

si une fonctionnalité statistique spécifique est nécessaire.

2.3 Machine Learning

Utiliser :

scikit-learn

Puis éventuellement :

XGBoost
LightGBM

uniquement après validation de l'intérêt des modèles classiques.

2.4 Visualisation

Utiliser :

matplotlib
seaborn
plotly

Les graphiques doivent être générés automatiquement dans :

reports/figures/
2.5 Tests

Utiliser :

pytest
2.6 Configuration

Utiliser :

YAML

Répertoire :

configs/
3. STRUCTURE DU PROJET

Structure obligatoire :

loto-research/
│
├── data/
│   ├── raw/
│   ├── validated/
│   ├── analytic/
│   ├── features/
│   ├── simulations/
│   └── predictions/
│
├── src/
│   ├── ingestion/
│   ├── validation/
│   ├── cleaning/
│   ├── statistics/
│   ├── temporal/
│   ├── anomalies/
│   ├── simulation/
│   ├── features/
│   ├── models/
│   ├── backtesting/
│   ├── prediction/
│   └── reporting/
│
├── tests/
│
├── experiments/
│
├── reports/
│   └── figures/
│
├── configs/
│
├── scripts/
│
├── notebooks/
│
└── docs/
4. DATA PIPELINE

Pipeline obligatoire :

SOURCE
  ↓
INGESTION
  ↓
RAW
  ↓
VALIDATION
  ↓
VALIDATED
  ↓
CLEANING
  ↓
ANALYTIC
  ↓
FEATURE ENGINEERING
  ↓
MODEL DATASET
  ↓
BACKTEST
  ↓
PREDICTION

Chaque étape doit produire un artefact identifiable.

5. DATA RAW

Le fichier source fourni par l'utilisateur doit être copié sans modification
dans :

data/raw/

Nom recommandé :

loteriema_YYYYMMDD_original.xlsx

Calculer :

SHA256

du fichier.

Créer :

data/raw/MANIFEST.json

Format :

{
  "filename": "loteriema.xlsx",
  "sha256": "...",
  "size_bytes": 0,
  "import_timestamp": "...",
  "source": "user_upload"
}
6. SCHÉMA CANONIQUE

Créer :

draw_id
date
draw_number_source
n1
n2
n3
n4
n5
n6
bonus
year
month
day
weekday

Types :

draw_id              string
date                 datetime64
draw_number_source   Int64
n1..n6               Int64
bonus                Int64
year                 Int16
month                Int8
day                  Int8
weekday              category
7. IDENTIFIANT

Ne jamais utiliser :

draw_number_source

comme identifiant global.

Créer :

draw_id = SHA256(
    date +
    draw_number_source +
    n1...n6 +
    bonus
)

Le hash doit être tronqué uniquement si une collision-safe policy
est documentée.

8. VALIDATION

Créer :

src/validation/schema.py
src/validation/rules.py

Tests obligatoires :

V001

Date valide.

V002

n1..n6 dans [1,49].

V003

Aucun doublon parmi n1..n6.

V004

bonus dans [1,49].

V005

Les valeurs sont numériques.

V006

Pas de colonnes obligatoires manquantes.

V007

Les dates peuvent être triées chronologiquement.

9. INVALID RECORDS

Toute ligne invalide doit être exportée :

data/validated/invalid_records.csv

avec :

row_number
reason
original_values
validation_rule

Aucune suppression silencieuse.

10. RÈGLE DES DATES DUPLIQUÉES

Pour le dataset ANALYTIC :

df.drop_duplicates(
    subset=["date"],
    keep="first"
)

Mais cette suppression ne doit jamais toucher RAW.

Exporter :

data/validated/duplicate_dates.csv
11. DATASET ANALYTIC

Créer :

data/analytic/draws.parquet

Ce fichier est la référence principale de toutes les analyses.

Il doit être immuable pour une version donnée.

Chaque modification crée :

dataset_version
12. VERSIONNAGE DATASET

Format :

DATASET_v001
DATASET_v002
...

Créer :

dataset_manifest.json

contenant :

{
  "dataset_version": "DATASET_v001",
  "source_hash": "...",
  "row_count": 0,
  "date_min": "...",
  "date_max": "...",
  "created_at": "..."
}
13. STATISTIQUES DE BASE

Module :

src/statistics/descriptive.py

Fonctions :

number_frequencies()
bonus_frequencies()
annual_frequencies()
monthly_frequencies()
sum_distribution()
odd_even_distribution()
low_high_distribution()
14. FRÉQUENCE THÉORIQUE

Pour un numéro principal :

p = 6 / 49

Pour N tirages :

expected = N * 6 / 49

La variance marginale théorique du nombre d'apparitions d'un numéro
sur N tirages est :

N * p * (1-p)
15. CHI-SQUARE

Module :

src/statistics/uniformity.py

Fonction :

chi_square_uniformity(observed, expected)

Retour :

{
    "chi2": ...,
    "df": ...,
    "p_value": ...,
    "n": ...
}

Ne jamais utiliser uniquement :

p < 0.05

sans correction lorsque plusieurs hypothèses sont testées.

AMENDEMENT A1 (2026-09-28) — référence Monte-Carlo pour l'uniformité
chi_square_uniformity() doit retourner, en plus de chi2/df/p_value/n :
    "p_value_monte_carlo", "expected_statistic_null" (≈ 43 pour 6/49), "n_simulations", "seed".
La p-value Monte-Carlo est la p-value de référence. df = 48 n'est PAS la loi nulle (voir Cahier §12, A1).
Test unitaire obligatoire : sous synthetic_uniform, le taux de rejet à alpha=0.05 doit être ≈ 5 %
(tolérance à documenter) — ce test aurait détecté l'erreur df = 48.

AMENDEMENT A2 (2026-09-28) — module src/loto_research/statistics/information.py
Fonctions : entropy(), kl_divergence_to_uniform(), jensen_shannon(), fisher_information_bernoulli().
Déclaration de famille : pour une distribution empirique de fréquences, chi2, G-test, KL à l'uniforme
et entropie sont des transformations d'une même information (KL = log49 - H ; G = 2·(6N)·KL ;
chi2 ≈ approximation d'ordre 2). Elles forment UNE SEULE FAMILLE de tests d'uniformité, avec un test
primaire désigné avant analyse (voir HYPOTHESES.md, A2). Les autres sont rapportées comme descriptives.
Fisher : I(p)=1/(p(1-p)) est une fonction de p ; statistique DESCRIPTIVE uniquement, jamais un test
de détection de changement (utiliser CUSUM / rapport de vraisemblance / ruptures).
Finite Free Probability : NON retenue (aucune question testable identifiée).

AMENDEMENT A3 (2026-09-28) — tests de permutation de l'ordre des tirages
Ajouter dans src/loto_research/temporal/ : permutation_tests.py et ljung_box (via statsmodels).
Permuter l'ordre chronologique des tirages (contenu de chaque tirage inchangé) donne une loi nulle
exacte pour toute statistique de dépendance temporelle (répétitions, autocorrélation, runs).
Toute permutation est seedée (numpy.random.Generator) et le nombre de permutations est journalisé.
Aucun nouveau dossier de premier niveau n'est créé (statistics/, temporal/, simulation/, backtesting/ suffisent).

16. MULTIPLE TESTING

Module :

src/statistics/multiple_testing.py

Implémenter :

bonferroni()
holm()
fdr_bh()

Chaque expérience doit enregistrer :

number_of_tests
raw_p_value
adjusted_p_value
method
17. GAPS

Module :

src/temporal/gaps.py

Pour chaque numéro :

gap_current
gap_mean
gap_median
gap_std
gap_max
gap_min

Construire également l'historique complet des gaps.

18. ATTENTION AUX GAPS

Ne jamais transformer :

long gap

en :

probabilité future supérieure

sans test empirique hors-échantillon.

19. AUTOCORRÉLATION

Analyser :

somme des numéros ;
nombre de pairs ;
fréquence individuelle ;
répétitions ;
indicateurs binaires par numéro.

Utiliser :

statsmodels

lorsque pertinent.

20. RUNS TEST

Tester des représentations binaires :

pair / impair
bas / haut
apparition / non-apparition

Conserver :

statistic
p_value
21. RÉPÉTITIONS

Pour deux tirages successifs :

intersection = len(set(draw_t) & set(draw_t_minus_1))

Construire la distribution :

0
1
2
3
4
5
6

Comparer avec Monte-Carlo sous H0.

22. SOMMES

Calculer :

sum(n1...n6)

Analyser :

moyenne ;
médiane ;
variance ;
quantiles ;
distribution ;
stabilité temporelle.
23. PAIRS

Générer :

itertools.combinations(range(1,50), 2)

Soit :

1176

paires possibles.

Pour chaque paire :

observed_count
expected_count
deviation
p_value
adjusted_p_value
24. TRIPLETS

Générer :

itertools.combinations(range(1,50), 3)

Soit :

18424

triplets.

Ne pas tester naïvement toutes les hypothèses avec un seuil brut de 5 %.

Utiliser :

FDR

et validation hors-échantillon.

25. MONTE CARLO

Module :

src/simulation/monte_carlo.py

Fonction générique :

simulate_draws(
    n_draws,
    n_simulations,
    seed
)

Chaque tirage simulé doit :

choisir 6 numéros distincts parmi 1..49
26. REPRODUCTIBILITÉ

Toutes les simulations doivent recevoir :

seed

Le seed doit être enregistré dans le rapport.

27. DISTRIBUTION NULLE

Pour chaque statistique :

observed_statistic

comparer :

simulated_statistics

Calculer :

empirical_p_value

avec correction appropriée.

28. CHANGE POINT

Module :

src/anomalies/change_points.py

Tester uniquement après l'analyse descriptive.

Méthodes possibles :

CUSUM ;
ruptures ;
Bayesian change point.

Chaque rupture doit être ensuite validée sur une période indépendante.

29. FEATURE ENGINEERING

Module :

src/features/build.py

Features possibles :

frequency_last_10
frequency_last_20
frequency_last_50
frequency_last_100
frequency_last_250
gap
rolling_frequency
pair_frequency
triplet_frequency
sum_statistics
odd_count
low_count
recent_overlap
30. RÈGLE ABSOLUE DES FEATURES

Pour prédire le tirage T :

toutes les features doivent être calculées avec les données < T

Jamais avec T.

31. DATASET SUPERVISÉ

Créer une observation par :

(draw_date, number)

avec cible :

target = 1

si le numéro apparaît dans le tirage.

Sinon :

target = 0

Attention aux dépendances structurelles dues au fait qu'exactement 6 numéros
sont sélectionnés par tirage.

32. BASELINE

Premier modèle obligatoire :

uniform_random

avec :

P(number) = 6/49

Deuxième baseline :

rolling_frequency

Aucun modèle ML ne doit être évalué sans ces baselines.

33. MODÈLES

Ordre obligatoire :

1. Random baseline
2. Frequency baseline
3. Logistic Regression
4. Random Forest
5. Gradient Boosting
6. XGBoost
7. LightGBM
8. Neural Network

Un modèle complexe ne doit être ajouté que si le modèle précédent justifie
l'expérience.

34. HYPERPARAMETER TUNING

Interdit :

tuning sur tout l'historique

Utiliser :

TimeSeriesSplit

ou un système walk-forward personnalisé.

35. WALK-FORWARD

Pseudo-code :

for t in prediction_points:

    train = data[data.date < t]

    model.fit(train)

    prediction = model.predict_proba(current_features)

    freeze_prediction(prediction)

    observe_real_result()

    evaluate(prediction, real_result)
36. DATA LEAKAGE TEST

Créer un test automatisé :

test_no_future_features()

Il doit vérifier que chaque feature utilisée à la date T possède :

max_source_date < T
37. PRÉDICTION FIGÉE

Format :

prediction_YYYYMMDD.json

Exemple :

{
  "prediction_id": "...",
  "prediction_date": "2026-09-27",
  "dataset_version": "DATASET_v001",
  "model_version": "MODEL_v003",
  "features_version": "FEATURES_v002",
  "numbers": [
    {
      "number": 1,
      "probability": 0.0
    }
  ],
  "generated_at": "...",
  "seed": 12345
}
38. HASH DE PRÉDICTION

Calculer SHA256 du fichier de prédiction.

Après le tirage, vérifier que le fichier original n'a pas changé.

39. ÉVALUATION

Module :

src/backtesting/evaluate.py

Métriques :

log_loss
Brier score
top_k_hit_rate
calibration
number_hit_count
40. PERFORMANCE DES COMBINAISONS

Ne pas utiliser uniquement :

jackpot gagné / perdu

car l'événement est extrêmement rare.

Mesurer également :

nombre de bons numéros
distribution des hits
probabilité moyenne attribuée aux numéros réellement sortis
41. CALIBRATION

Comparer :

probabilité prédite
vs
fréquence réellement observée

Créer un reliability diagram.

42. ENSEMBLE

Après validation individuelle :

ensemble =
weighted_average(
    statistical_model,
    ML_model,
    temporal_model
)

Les poids doivent être déterminés uniquement avec les données disponibles
au moment correspondant.

43. IA LOCALE

L'IA locale est une couche d'analyse.

Elle ne doit pas modifier directement les données.

Elle reçoit :

statistical reports
model reports
backtest results
anomaly reports

et produit :

hypotheses
research questions
interpretations

Toute conclusion de l'IA doit être vérifiable par des calculs.

44. ARCHITECTURE IA
DATA
 ↓
PYTHON STATISTICAL ENGINE
 ↓
ML ENGINE
 ↓
RESULT DATABASE
 ↓
LOCAL LLM
 ↓
SCIENTIFIC REPORT

Le LLM n'est jamais la source primaire d'un résultat numérique.

45. EXPERIMENT REGISTRY

Créer :

experiments/registry.csv

Colonnes :

experiment_id
date
dataset_version
feature_version
model_version
hypothesis
parameters
seed
result
status
46. STATUS D'UNE HYPOTHÈSE

Valeurs autorisées :

UNTESTED
EXPLORATORY
SUPPORTED
REJECTED
REPLICATED
PREDICTIVE
FAILED_OUT_OF_SAMPLE
47. EXPLORATOIRE VS CONFIRMATOIRE

Chaque analyse doit être marquée :

EXPLORATORY

ou :

CONFIRMATORY

Une hypothèse découverte après observation des données ne doit pas devenir
rétroactivement confirmatoire.

48. RAPPORTS

Générer :

reports/
├── DATA_QUALITY.md
├── DESCRIPTIVE.md
├── UNIFORMITY.md
├── TEMPORAL.md
├── GAPS.md
├── PAIRS.md
├── TRIPLETS.md
├── ANOMALIES.md
├── MONTE_CARLO.md
├── MODELS.md
├── BACKTEST.md
└── FINAL.md
49. JOURNAL D'EXÉCUTION

Chaque pipeline doit produire :

logs/run_YYYYMMDD_HHMMSS.json

avec :

{
  "run_id": "...",
  "timestamp": "...",
  "dataset_version": "...",
  "git_commit": "...",
  "python_version": "...",
  "dependencies": {},
  "seed": 12345
}
50. GIT

Avant chaque expérience :

git status
git rev-parse HEAD

Enregistrer le commit utilisé.

Une expérience doit être reproductible à partir du commit enregistré.

51. TESTS UNITAIRES

Minimum obligatoire :

tests/
├── test_validation.py
├── test_cleaning.py
├── test_statistics.py
├── test_gaps.py
├── test_simulation.py
├── test_features.py
├── test_no_leakage.py
├── test_backtesting.py
└── test_prediction_freeze.py
52. TESTS STATISTIQUES DU MOTEUR

Le moteur doit être testé sur des données synthétiques dont les propriétés
sont connues.

Créer notamment :

synthetic_uniform
synthetic_biased
synthetic_dependent
synthetic_regime_change

Le système doit être capable de retrouver les anomalies artificiellement
introduites avec des taux d'erreur documentés.

53. BENCHMARK

Créer un benchmark :

uniform_random
biased_simulation
historical_loto

Comparer les performances.

54. CRITÈRE DE VALIDITÉ D'UN SIGNAL

Un signal n'est considéré comme robuste que s'il :

apparaît dans les données historiques ;
survit aux corrections statistiques pertinentes ;
possède une taille d'effet mesurable ;
n'est pas expliqué par une erreur de données ;
n'est pas uniquement dû à une période particulière ;
survit à une validation hors-échantillon ;
est reproductible.
55. INTERDICTION DU DATA MINING NON CONTRÔLÉ

Interdit de faire :

for hypothesis in thousands_of_hypotheses:
    if p < 0.05:
        print(hypothesis)

sans enregistrer :

nombre total de tests

et appliquer une correction.

56. P-HACKING

Le système doit détecter les expériences où :

plusieurs fenêtres temporelles ont été essayées ;
plusieurs seuils ont été essayés ;
plusieurs modèles ont été essayés ;
seules les meilleures performances ont été conservées.

Créer :

research_audit.json
57. RECHERCHE DE PRÉDICTIBILITÉ

Le système doit répondre à la question :

Les données historiques permettent-elles d'améliorer les probabilités futures
par rapport à une sélection uniforme ?

Test principal :

H0:
modèle <= baseline

contre :

H1:
modèle > baseline

sur données hors-échantillon.

58. SEUIL DE DÉCISION

Ne pas définir arbitrairement :

accuracy > X

Le seuil doit dépendre de la métrique et du problème.

Rapporter :

effect size
confidence interval
p-value
adjusted p-value
out-of-sample performance
59. INTERPRÉTATION

Chaque rapport doit séparer :

OBSERVATION
CALCUL
INTERPRÉTATION
LIMITATION
60. NOUVEAU TIRAGE

Lorsqu'un nouveau tirage est ajouté :

1. validation
2. archivage
3. évaluation des prédictions précédentes
4. ajout au dataset
5. nouvelle version dataset
6. recalcul des features
7. réentraînement éventuel
8. nouvelle prédiction
61. AUCUNE MODIFICATION RÉTROACTIVE

Une prédiction passée ne doit jamais être recalculée avec les données futures
pour être présentée comme une prédiction historique.

Si elle est recalculée à des fins d'analyse :

REANALYSIS

doit être explicitement indiqué.

62. MODE RECHERCHE

Le programme doit pouvoir fonctionner :

python -m loto_research.pipeline --mode research
63. MODE BACKTEST
python -m loto_research.pipeline --mode backtest
64. MODE PREDICTION
python -m loto_research.pipeline --mode prediction
65. MODE UPDATE
python -m loto_research.pipeline --mode update
66. MODE FULL
python -m loto_research.pipeline --mode full
67. CONFIGURATION

Créer :

configs/default.yaml

Exemple :

data:
  main_numbers: 49
  numbers_per_draw: 6
  duplicate_date_policy: keep_first

statistics:
  alpha: 0.05
  multiple_testing: holm

simulation:
  n_simulations: 100000
  seed: 42

backtest:
  minimum_training_draws: 500
  walk_forward: true

models:
  baseline_random: true
  logistic_regression: true
  random_forest: true
  xgboost: true
  lightgbm: false
  neural_network: false
68. ENVIRONNEMENT

Créer :

pyproject.toml

et verrouiller les dépendances.

Exemple :

pandas
numpy
scipy
statsmodels
scikit-learn
openpyxl
pyarrow
matplotlib
pytest
pyyaml

Ajouter XGBoost/LightGBM uniquement lorsqu'ils sont nécessaires.

69. PERFORMANCE

Les analyses doivent être vectorisées lorsque possible.

Éviter :

for row in dataframe.iterrows()

pour les traitements massifs.

Utiliser :

numpy ;
pandas ;
groupby ;
vectorisation.
70. MÉMOIRE

Pour les analyses de millions de simulations :

ne pas conserver inutilement toutes les matrices en RAM.

Utiliser :

batch simulation ;
agrégation progressive ;
Parquet ;
générateurs.
71. RANDOMNESS

Toutes les fonctions aléatoires doivent utiliser :

numpy.random.Generator

et non le générateur global.

Exemple :

rng = np.random.default_rng(seed)
72. SÉCURITÉ SCIENTIFIQUE

Le système doit empêcher :

modification silencieuse des résultats ;
remplacement d'une prédiction passée ;
suppression d'expériences ;
changement de seed sans journalisation.
73. FINAL REPORT

Le rapport final doit répondre explicitement :

1. Les données sont-elles propres ?
2. Les numéros sont-ils compatibles avec l'uniformité ?
3. Le complémentaire présente-t-il une anomalie robuste ?
4. Existe-t-il une dépendance temporelle ?
5. Existe-t-il des ruptures ?
6. Existe-t-il des structures persistantes ?
7. Les modèles ML améliorent-ils le hasard ?
8. Cette amélioration survit-elle au backtesting ?
9. Est-elle stable dans le temps ?
10. Existe-t-il une capacité prédictive mesurable ?
74. RÈGLE FINALE

Le système ne doit jamais confondre :

motif

avec :

signal

ni :

signal historique

avec :

pouvoir prédictif

La seule preuve pertinente de prédictibilité est une amélioration
reproductible, prospective ou strictement hors-échantillon, comparée à une
baseline correctement définie.

75. ORDRE D'IMPLÉMENTATION

Claude doit implémenter exactement dans cet ordre :

PHASE 01
Ingestion

PHASE 02
Validation

PHASE 03
Cleaning

PHASE 04
Dataset versioning

PHASE 05
Descriptive statistics

PHASE 06
Uniformity tests

PHASE 07
Temporal analysis

PHASE 08
Gap analysis

PHASE 09
Pair/triplet analysis

PHASE 10
Monte-Carlo

PHASE 11
Anomaly detection

PHASE 12
Feature engineering

PHASE 13
Baselines

PHASE 14
Machine Learning

PHASE 15
Walk-forward backtesting

PHASE 16
Model comparison

PHASE 17
Ensemble

PHASE 18
Prediction freezing

PHASE 19
Future draw integration

PHASE 20
Continuous evaluation

PHASE 21
Local AI research assistant
76. CONDITION DE PASSAGE ENTRE PHASES

Claude ne doit pas passer automatiquement à la phase suivante.

Chaque phase doit produire :

CODE
TESTS
RESULTATS
RAPPORT
DECISION

Statut :

PASS
FAIL
BLOCKED

Une phase FAIL bloque les phases suivantes.

Une phase BLOCKED doit expliquer précisément ce qui manque.

77. INSTRUCTION FINALE À CLAUDE

Tu es l'ingénieur scientifique chargé d'implémenter cette spécification.

Tu dois :

privilégier la rigueur à la complexité ;
privilégier la reproductibilité à la performance apparente ;
rechercher activement les erreurs de données ;
rechercher activement les explications alternatives ;
comparer chaque modèle au hasard ;
empêcher les fuites temporelles ;
enregistrer toutes les expériences ;
ne jamais supprimer un résultat défavorable ;
ne jamais modifier rétroactivement une prédiction ;
ne jamais transformer une corrélation en causalité ;
ne jamais présenter une anomalie statistique comme une preuve de fraude ;
ne jamais considérer une faible p-value isolée comme une preuve suffisante ;
toujours distinguer exploration et confirmation.

Tu dois pouvoir conclure que le système ne possède aucun pouvoir prédictif
si les expériences l'indiquent.

Le but n'est pas de fabriquer une prédiction convaincante.

Le but est de déterminer, avec le maximum de rigueur possible, ce que les
données permettent réellement de savoir.