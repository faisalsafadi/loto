# SPEC_V2 — Boîte à outils d'audit statistique des loteries (v2)

Statut : **PROPOSITION, à valider avant tout code** — 2026-10-14
Base : LOTO MAROC Research Engine v1 (Phases 0 à 10, clôture 2026-10-08, `FINAL.md`)

## 1. Objectif et non-objectifs

**Objectif.** Un outil open source qui permet à n'importe qui de stocker les tirages d'une loterie
« k numéros parmi N », de les auditer statistiquement avec les garde-fous du projet v1, et de
tester les détecteurs sur des tirages simulés dont on connaît la vérité.

**Non-objectifs** (écrits en tête du README) :
- Ce n'est pas un outil de prédiction ni de pronostic. Le résultat de v1 est négatif et reste affiché.
- Aucun classement de numéros « favoris » ni « déconseillés ».
- Aucune conclusion de fraude : les sorties possibles restent « aucune anomalie détectée »,
  « anomalie statistique » ou « anomalie robuste nécessitant investigation » (Cahier §37).

## 2. Principes hérités de v1

1. Pré-enregistrement avant de regarder les données ; tout ajout a posteriori est `POST_HOC`.
2. Données réelles en **ajout seul** ; une correction est une nouvelle ligne, jamais une édition.
3. Tirages simulés et tirages réels ne se mélangent jamais (tables séparées).
4. Tout lancement d'analyse est journalisé ; chaque correction de comparaisons multiples tient compte
   de tous les tests déjà faits.
5. Aucune fuite temporelle (test de non-fuite conservé dans la CI).
6. Une conclusion négative est un résultat valide.

## 3. Règle anti-peeking (cœur scientifique de v2)

Relancer l'analyse à chaque nouveau tirage multiplie les occasions de faux positif. Règle :

- Une hypothèse **pré-enregistrée** porte une date `registered_at` et un effectif cible `n_star`.
  Elle n'est testée que sur les tirages dont la **date de tirage** (pas la date d'import) est
  postérieure à `registered_at`. Un tirage ancien ajouté plus tard ne compte pas.
- **Un seul test confirmatoire** par hypothèse, quand `n_star` est atteint. Avant, les relances
  affichent des résultats étiquetés `DESCRIPTIVE` (jamais de p « significatif » mis en avant).
- Les hypothèses `EXPLORATORY` / `POST_HOC` ne deviennent jamais confirmatoires sur les données qui
  les ont suggérées (cas de H009 en v1).
- `loto analyze` affiche le nombre cumulé de tests de la base et applique la correction sur la famille
  complète.

## 4. Modules

| Module | Contenu | Commande |
|---|---|---|
| Jeu | Configuration k, N, règle du complémentaire (ex. 6/49 exclusif, 5/39) | `loto game create` |
| Données | Import xlsx/CSV, ajout manuel, validation (règles V001–V007 généralisées), provenance par ligne | `loto import`, `loto add` |
| Analyse | Phases v1 rendues paramétrables : uniformité, gaps, paires/triplets, temporel, backtest | `loto analyze` |
| Registre | Enregistrer une hypothèse (H0, H1, test, correction, `n_star`) avant de la tester | `loto hypothesis add` |
| Simulateur | Tirages sous H0 avec seed ; biais injectable (numéro, paire, dépendance, rupture) | `loto simulate` |
| Banc d'essai | Taux de détection et de faux positifs du moteur sur des biais connus | `loto benchmark` |
| Tableau de bord | Streamlit, lecture seule sur la base (§6) | `loto dashboard` |

Hors v2.0 (table réservée, pas de code) : prédictions figées de la Phase 11, couche d'IA locale.
Question ouverte : des combinaisons aléatoires « à jouer » (voir §9).

## 5. Base de données (SQLite, un fichier)

- `games(id, name, k, n_max, bonus_range, bonus_exclusive, notes)`
- `draws(id, game_id, draw_date, source_draw_no, numbers_json, bonus, source, source_ref, ingested_at,
  row_sha256)` : ajout seul, mises à jour et suppressions interdites par déclencheur SQL
- `draw_corrections(id, draw_id, field, old_value, new_value, reason, author, at)`
- `simulated_runs(id, game_id, seed, model, params_json, created_at)` et
  `simulated_draws(run_id, idx, numbers_json, bonus)`
- `hypotheses(id, game_id, h0, h1, test, correction, kind, registered_at, n_star, status)` avec
  `kind` ∈ {PRE_REGISTERED, EXPLORATORY, POST_HOC}
- `analysis_runs(id, started_at, git_commit, dataset_hash, n_draws, config_json)`
- `test_results(id, run_id, hypothesis_id, statistic, p_raw, p_adjusted, method, family_size, tag)`
  avec `tag` ∈ {CONFIRMATORY, DESCRIPTIVE}

## 6. Interface : garde-fous

Pages : Données, Fréquences (intervalles de confiance), Tests (p ajustés), Journal des lancements,
Simulateur et banc d'essai, À propos.
- Bandeau permanent : « Toute combinaison a la même probabilité (1 sur C(N,k)). »
- Pas de tri par « chaud » ou « en retard » ; les fréquences sont présentées avec leur intervalle
  de confiance et l'écart attendu par hasard.
- Le résultat négatif de v1 est consultable depuis la page « À propos ».

## 7. Dépôt et gouvernance GitHub

- Paquet Python installable, commandes via Typer, tests pytest, CI GitHub Actions (tests + test de
  non-fuite + formatage).
- Licence : MIT par défaut (alternative : Apache-2.0).
- `README` en français et en anglais, résultat négatif en tête ; `CONTRIBUTING` : hypothèse déclarée
  avant de regarder les données, tests obligatoires, interdiction d'éditer les données réelles.
- Modèles d'issue (« proposition d'hypothèse » : H0, H1, test, correction) et de PR (cases à cocher).
- `CODE_OF_CONDUCT`, avertissement sur les jeux d'argent.
- Les rapports v1 sont conservés en français dans `docs/research/` comme archive de référence.

## 8. Données et droits (à traiter avant la première publication)

- Vérifier les conditions d'utilisation du site de la loterie avant de redistribuer les résultats ;
  à défaut, publier un jeu synthétique et un script d'import que chacun lance sur ses propres données.
- Le fichier source de v1 a été réparé sans journal : documenter la provenance, ou le remplacer par un
  import vérifié contre la source officielle.
- Ne jamais commiter les PDF de livres (droits d'auteur) ni de chemins personnels.

## 9. Décisions à valider

| # | Décision | Proposition par défaut | Alternative |
|---|---|---|---|
| D1 | Base de données | SQLite | PostgreSQL |
| D2 | Interface | Ligne de commande, puis Streamlit | Web complète (FastAPI + front) |
| D3 | « Générer des tirages » | Simulateur sous H0 avec biais injectable, banc d'essai | + combinaisons aléatoires à jouer |
| D4 | Généralisation k parmi N | Oui, dès v2.0 | Loto Maroc 6/49 seulement |
| D5 | Langue du code et des docs | Code et CLI en anglais, README bilingue | Tout en français |
| D6 | Licence | MIT | Apache-2.0 |
| D7 | Données réelles dans le dépôt | Non, jeu synthétique + import | Oui si les conditions d'utilisation le permettent |
| D8 | Prédictions figées (Phase 11) | Hors v2.0 | Incluses, étiquetées « non validées » |

## 10. Jalons (chacun avec un verdict GO / NO-GO)

| Jalon | Contenu | Critère GO |
|---|---|---|
| M1 | Base SQLite, import de DATASET_v001 (parquet), validation, déclencheurs d'ajout seul | 3155 tirages importés, numéros/complémentaire/dates identiques au parquet, SHA256 du RAW en provenance, UPDATE et DELETE refusés. **Verdict : GO (2026-10-14)** |
| M2 | Commande `loto analyze` autour des phases v1 | Résultats identiques à v1 (mêmes p, seed 42) |
| M3 | Registre d'hypothèses et règle anti-peeking | Test refusé avant `n_star` ; test sur tirage antérieur à `registered_at` refusé |
| M4 | Simulateur et banc d'essai | Taux de faux positifs proche de 5 % sous H0 ; taux de détection documenté par taille de biais |
| M5 | Tableau de bord | Garde-fous du §6 vérifiés à la main |
| M6 | Documentation, licence, CI, nettoyage | Un inconnu installe et lance le banc d'essai en suivant le README |

## 11. Risques

- Public : l'outil peut être pris pour un générateur de pronostics. Réponse : non-objectifs en tête,
  bandeau, pas de classement de numéros.
- Données : droits de redistribution et provenance non résolus.
- Charge : M1 à M6 sont plusieurs jalons de travail ; on les enchaîne un par un, avec validation.
