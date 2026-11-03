# Prédictions exploratoires figées — protocole pré-enregistré / Pre-registered protocol

**English summary.** Before each draw, the tool freezes (SHA256, UTC timestamp, append-only) the probabilities of
three fixed models for the *next* draw only: uniform random, smoothed frequency, logistic regression (the models of the
audit). After the draw, each frozen prediction is scored against uniform random. Status: **NOT VALIDATED**: in the
audit, no model beat chance out of sample. Hypothesis **H010** (pre-registered below) is tested **once**, after 500
scored predictions. Do not use this as a betting tip: every combination has a probability of 1 in 13,983,816.

---

## 1. Statut et objectif

- Statut permanent : **NON VALIDÉ**. L'audit (H008, 2 655 tirages en walk-forward) a montré qu'aucun modèle ne bat
  le hasard hors échantillon.
- Objectif : obtenir, **dans le temps**, la seule preuve acceptable d'un pouvoir prédictif (Niveau D du Cahier des
  charges) : une amélioration sur des tirages **jamais vus** au moment de la prédiction.
- Ce n'est pas un conseil de jeu. Toute combinaison a **1 chance sur 13 983 816**. Une « variante » n'a aucun
  avantage démontré : elle sert à mesurer.

## 2. Règles de gel

| Règle | Application |
|---|---|
| Un seul tirage visé | Le **prochain** tirage seulement (au plus 7 jours après le dernier tirage en base) |
| Date du tirage | Calculée : prochain lundi, mercredi ou samedi. Rythme observé depuis 2016, à confirmer pour chaque tirage (jour férié possible) |
| Avant le tirage | Gel possible seulement **avant le jour du tirage** (déclencheur SQL sur la date UTC) |
| Une par tirage | Contrainte d'unicité : impossible de figer deux fois le même tirage |
| Jamais modifiable | Table en ajout seul (déclencheurs `UPDATE` et `DELETE` refusés) |
| Empreinte | SHA256 du fichier JSON `data/predictions/prediction_AAAAMMJJ.json`, recopiée dans la base |
| Preuve publique | Le fichier doit être **commité et poussé sur GitHub avant le tirage** : la date du dépôt public fait foi |
| Données à jour | Refus s'il manque un tirage en base (sauf forçage explicite, noté dans le fichier) |

## 3. Les trois modèles (fixés, jamais modifiés)

1. **uniform_random** : probabilité 6/49 pour chaque numéro. Sa « combinaison » est un tirage de contrôle dont la
   graine dérive de la date cible (reproductible, impossible à re-tirer).
2. **frequency** : fréquence lissée, pseudo-compte alpha = 10 ancré sur 6/49 (amendement A9). Combinaison : les 6 numéros
   de plus forte probabilité.
3. **logistic** : régression logistique, C = 1,0, variables de la Phase 8, réajustée sur tout l'historique avant chaque
   prédiction (amendements A9, A10). Combinaison : les 6 numéros de plus forte probabilité.

Tout autre modèle, toute autre variante ou tout autre réglage est une **nouvelle hypothèse `POST_HOC`**, jamais une
modification de celles-ci. Essayer des modèles jusqu'à en trouver un qui gagne est du p-hacking.

## 4. Hypothèse H010 (pré-enregistrée avant la première prédiction)

| Champ | Valeur |
|---|---|
| ID | H010 |
| Type | PRE_REGISTERED, CONFIRMATORY |
| H0 | Pour chacun des modèles `frequency` et `logistic`, le log loss moyen sur les prédictions figées n'est pas inférieur à celui du hasard uniforme |
| H1 | Le log loss moyen du modèle est **inférieur** à celui du hasard uniforme (sens unique) |
| Variable | Différence appariée par tirage : log loss du modèle − log loss du hasard uniforme (moyenne sur les 49 numéros) |
| Test | Wilcoxon des rangs signés, unilatéral, comme en Phase 9 |
| Correction | Holm sur les 2 comparaisons, alpha = 0,05 |
| `n_star` | **500 prédictions évaluées** (environ 3 ans et 2 mois), test **unique** quand 500 est atteint |
| Données | Uniquement les prédictions figées **après** la date d'enregistrement de ce protocole, avant leur tirage |
| Avant `n_star` | Résumés **descriptifs** seulement (écart moyen et intervalle) : aucun p-value n'est lu |
| Descriptif secondaire | Nombre de bons numéros de chaque combinaison, comparé à l'espérance 36/49 ≈ 0,735 (aucun test) |

**Lecture honnête du résultat attendu.** En Phase 10, les deux modèles étaient *moins bons* que le hasard (écart moyen
de +0,000366 et +0,000057 en log loss). La puissance du test à 500 prédictions sur un éventuel gain minuscule est
inconnue et probablement faible : le résultat le plus vraisemblable est « H0 non rejetée ». Un rejet serait une
**réplication prospective d'un écart statistique**, pas encore une preuve d'exploitabilité.

## 5. Ce que ce protocole ne fait pas

- Il ne promet pas de gagner et ne classe aucun numéro comme « meilleur » : les probabilités sont toutes proches de 6/49.
- Il ne change pas les conclusions de l'audit : les résultats de la v1 restent valables.
- Il ne conclut jamais à une fraude.

## 6. Modifier ou proposer une variante

Fork du dépôt, puis une **nouvelle** hypothèse déclarée avant de regarder les données (modèle, test, `n_star`). Ne jamais
modifier les prédictions figées ni la base : l'outil l'interdit exprès.
