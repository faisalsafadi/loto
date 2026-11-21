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
| Heure limite | Gel possible jusqu'à **15h00 UTC le jour du tirage** (environ 16h00 au Maroc, 15h00 pendant le ramadan ; amendement A11, 2026-11-05, précisé le 2026-11-09) ; l'heure limite est enregistrée avec la prédiction et contrôlée par un déclencheur SQL |
| Heure de référence | Lue en ligne (sites fiables) ; sans internet, horloge de l'ordinateur. Si les deux sont connues, la plus tardive est retenue. Source et écart sont enregistrés dans le fichier |
| Une par tirage | Contrainte d'unicité : impossible de figer deux fois le même tirage |
| Jamais modifiable | Table en ajout seul (déclencheurs `UPDATE` et `DELETE` refusés) |
| Empreinte | SHA256 du fichier JSON `data/predictions/prediction_AAAAMMJJ.json`, recopiée dans la base |
| Preuve publique (facultative) | Pour prouver à des tiers que la prédiction précède le tirage : déposer le fichier sur le dépôt public **avant le tirage** ; la date du dépôt public fait foi. Pour un usage personnel, le logiciel applique déjà l'heure limite avec son heure de référence |
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

## 4b. Hypothèse H011 — le complémentaire (pré-enregistrée le 2026-11-11, avant la première prédiction avec complémentaire)

| Champ | Valeur |
|---|---|
| ID | H011 |
| Type | PRE_REGISTERED, CONFIRMATORY |
| H0 | La fréquence lissée du complémentaire n'a pas un log loss moyen inférieur à celui du hasard uniforme sur les 49 valeurs |
| H1 | Le log loss moyen de la fréquence lissée est **inférieur** à celui du hasard uniforme (sens unique) |
| Variable | Par tirage : −ln(probabilité attribuée à la valeur réelle du complémentaire) moins ln 49 (hasard uniforme) |
| Modèles | Hasard uniforme (1/49 par valeur) ; fréquence lissée sur l'historique du complémentaire, pseudo-compte alpha = 10 réparti sur les 49 valeurs (même lissage qu'en A9) |
| Test | Wilcoxon des rangs signés, unilatéral, sur les écarts appariés par tirage |
| Correction | Aucune : une seule comparaison, alpha = 0,05 |
| `n_star` | **500 prédictions évaluées avec complémentaire**, test **unique** quand 500 est atteint |
| Données | Uniquement les prédictions figées à partir du 2026-11-11 (fichiers de format 2), avant leur tirage |
| Avant `n_star` | Résumés **descriptifs** seulement : aucun p-value n'est lu |
| Descriptif secondaire | Part des variantes dont le complémentaire proposé est le bon (attendu par hasard : 1 sur 49, soit 2,0 %), sans test |

**Variantes affichées.** A (fréquence) et B (logistique) proposent le complémentaire le plus probable selon la fréquence lissée
**hors de leurs 6 numéros** (le complémentaire ne peut pas être l'un d'eux). C est un tirage de contrôle hors de ses 6 numéros,
avec une graine dérivée de la date cible. Les variantes A et B partagent la même loi du complémentaire : seule la valeur
proposée diffère.

**Lecture honnête du résultat attendu.** L'audit n'a trouvé aucune structure exploitable sur le complémentaire : un seul
écart isolé (H002, p brut = 0,0235), non confirmé. Le résultat le plus vraisemblable est « H0 non rejetée ». Un rejet serait une
réplication prospective d'un écart statistique, pas une preuve d'exploitabilité.

## 5. Ce que ce protocole ne fait pas

- Il ne promet pas de gagner et ne classe aucun numéro comme « meilleur » : les probabilités sont toutes proches de 6/49.
- Il ne change pas les conclusions de l'audit : les résultats de la v1 restent valables.
- Il ne conclut jamais à une fraude.

## 6. Modifier ou proposer une variante

Fork du dépôt, puis une **nouvelle** hypothèse déclarée avant de regarder les données (modèle, test, `n_star`). Ne jamais
modifier les prédictions figées ni la base : l'outil l'interdit exprès.

## 7. Amendement A11 — heure limite de gel (2026-11-05)

- **Avant :** gel possible seulement avant le début du jour du tirage (00h00 UTC). **Après :** jusqu'à **15h00 UTC le
  jour du tirage**, soit environ 16h00 au Maroc (15h00 pendant le ramadan).
- **Précision du 2026-11-09 :** la première version de cet amendement fixait « 16h00, heure du Maroc » et la convertissait
  avec la base de fuseaux horaires de l'ordinateur. Cette base s'est révélée différente d'un système à l'autre (un test a
  donné un décalage de 0 h en novembre, alors que le Maroc est à UTC+1 hors ramadan). Pour ne pas dépendre d'une donnée
  externe, la limite est désormais une **heure fixe en UTC** : 15h00. Elle vaut au plus tard 16h00 locale, quelle que soit
  l'heure en vigueur au Maroc. Aucune prédiction n'avait été figée sous la première version.
- **Motif :** la règle précédente était plus stricte que nécessaire. Les données utilisables sont les mêmes (aucun tirage
  n'a lieu entre-temps) : l'amendement ne change ni les modèles, ni les données, ni l'hypothèse H010. Il ne fait que
  desserrer une contrainte de calendrier.
- **Ce qui compte :** que la prédiction soit figée avant que le résultat soit connu. Les résultats sont visibles à partir
  de 21h00, heure du Maroc (information déclarée, à vérifier) et le tirage physique a lieu avant cette heure : 15h00 UTC
  laisse une marge avant les deux.
- **Heure de référence :** lue en ligne, sinon horloge de l'ordinateur ; la plus tardive des deux est retenue ; la source et
  l'écart sont enregistrés dans le fichier figé.
- **Fuseau :** aucun : la limite est exprimée en UTC, sans conversion.
- **Portée :** prédictions figées à partir de cette date. La prédiction n° 1 (tirage du 2026-11-02) a été figée sous
  l'ancienne règle ; aucune prédiction existante n'est modifiée.
- Si l'heure du tirage ou de publication des résultats change, cette limite sera revue par un nouvel amendement daté.
