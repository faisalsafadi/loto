# H009 — prospective pre-registration / Pré-enregistrement prospectif

**English summary.** During the v1 audit (3155 draws, 2001-2026) we noticed, *after looking at the data*,
a small positive lag-1 autocorrelation for two values of the bonus ball (2 and 49). It was not retained
by Holm/Bonferroni, so it is an exploratory lead, tagged `POST_HOC`, and cannot be confirmed on the data
that suggested it. We therefore pre-register a **new** test, on **future draws only**: 2 hypotheses
(bonus = 2, bonus = 49), one-sided (positive), Bonferroni over the 2, to be run **once**, when
`n_star` ≈ 2,400 post-registration draws exist (≈ 15 years). The expected outcome is "not confirmed".
Fork the repo and register your own variant if you disagree: never edit this one.

---

## 1. D'où vient H009 (OBSERVATION)

- Pendant l'audit v1, une exploration (hors plan initial) a examiné l'autocorrélation d'ordre 1 de
  l'indicateur « le complémentaire vaut v », pour chaque valeur v de 1 à 49.
- Deux valeurs sortent : **v = 2** (ρ = +0,057, p = 0,00138) et **v = 49** (ρ = +0,056, p = 0,00157).
- Après correction **FDR-BH** (49 tests), elles passent (q = 0,039). Après **Holm / Bonferroni**, non.
- Statut dans `HYPOTHESES.md` : **H009, `POST_HOC`, `EXPLORATORY`**. Elle est née de l'observation des
  données : elle ne devient **jamais** confirmatoire sur ces données-là (règle du projet).

Autrement dit : avec 49 valeurs examinées, voir deux valeurs à p ≈ 0,0015 n'a rien d'extraordinaire
sous le hasard. C'est une piste, pas un résultat.

## 2. Ce que nous enregistrons maintenant

Une réplication prospective, **testée uniquement sur des tirages futurs** :

| Élément | Valeur |
|---|---|
| Hypothèses | une pour la valeur 2, une pour la valeur 49 (codes `H009R-2` et `H009R-49`) |
| H0 | l'indicateur « complémentaire = v » n'a pas d'autocorrélation d'ordre 1 |
| H1 | autocorrélation d'ordre 1 **positive** (sens fixé d'avance) |
| Test | `bonus_lag1` du catalogue (`src/loto_research/analysis/catalog.py`) |
| Famille | 2 hypothèses, correction **Bonferroni** : chacune testée à 0,05 / 2 = 0,025 |
| `n_star` | **2 400 tirages** postérieurs à la date d'enregistrement |
| Nombre de tests | **un seul** par hypothèse, quand `n_star` est atteint |
| Données | uniquement les tirages dont la **date de tirage** est strictement postérieure à la date d'enregistrement posée par l'outil (colonne `registered_date`, pas la date de ce document) |

## 3. Qu'est-ce que `n_star` ?

C'est le nombre de futurs tirages qu'on s'engage à attendre **avant de juger**, fixé **avant** de voir
le moindre résultat.

Pourquoi : si on relançait le test à chaque nouveau tirage en s'arrêtant dès que la p-value passe sous
0,05, on finirait presque toujours par trouver « quelque chose », même sous le hasard pur. Fixer
`n_star` supprime ce degré de liberté. L'outil applique la règle :

- avant `n_star` tirages postérieurs, le test confirmatoire est **refusé** (résultats descriptifs seulement) ;
- à `n_star`, le test utilise **exactement** les `n_star` premiers tirages postérieurs, même s'il y en a plus ;
- il n'y a **qu'un seul essai** : une fois consommé, il ne se refait pas.

## 4. Pourquoi 2 400 (CALCUL)

Pour détecter une corrélation ρ avec 80 % de puissance, à 0,025 unilatéral : `n ≈ ((1,96 + 0,84) / ρ)²`.
Avec ρ = 0,057 : **n ≈ 2 400**. Au rythme de 3 tirages par semaine (~156 par an), c'est **environ 15 ans**.

| n_star | délai approximatif | puissance si l'effet réel = 0,057 |
|---|---|---|
| 156 | 1 an | ~10 % |
| 780 | 5 ans | ~35 % |
| 2 400 | 15 ans | ~80 % |

## 5. Lire le résultat honnêtement (INTERPRÉTATION, fixée d'avance)

- **Piège du gagnant.** ρ = 0,057 a été mesuré *parce qu'il était élevé dans nos données*. L'effet réel est
  probablement plus faible. Si ρ réel = 0,028 (moitié), la puissance à 2 400 tirages tombe à **~30 %**.
- **Non confirmé** (p > 0,025) : cela **ne réfute pas** H009, vu cette puissance. Cela signifie « non
  soutenue à ce niveau de puissance ».
- **Confirmé** (p ≤ 0,025 pour au moins une valeur) : c'est une réplication prospective d'un écart
  statistique. **Ce n'est pas un pouvoir prédictif** (Niveau D du Cahier des charges). Même vraie, une
  autocorrélation de 0,057 explique moins de **0,4 %** de la variance, soit un gain négligeable.
- Dans tous les cas : jamais de conclusion de fraude. Le résultat est publié **quelle que soit l'issue**.

## 6. Pour que l'enregistrement soit crédible (LIMITATION)

- La base SQLite n'est pas dans Git. L'enregistrement n'est vérifiable par un tiers que s'il est
  **recopié dans `HYPOTHESES.md`, commité et poussé sur GitHub avant l'arrivée des tirages concernés** : la
  date du dépôt public fait foi. Un horodatage Git purement local est falsifiable.
- Les tirages futurs doivent être ajoutés avec leur source (`source`, `source_ref`). À ce jour, la commande
  d'ajout de tirages n'est pas encore écrite (voir la feuille de route).
- Ce test confirme ou non **une piste précise**. Il ne dit rien du reste du jeu.

## 7. Modifier ou proposer une variante

Tu n'es pas d'accord (autre valeur, autre `n_star`, autre sens) ? Très bien :

1. **N'édite jamais** cet enregistrement ni la base : l'outil l'interdit exprès (tables en ajout seul).
2. **Fais ta propre hypothèse** avec `loto hypothesis add` (voir `--help`) : tu fixes toi-même H0, H1, le
   test, la correction, `n_star`. Elle aura sa propre date, et seuls les tirages postérieurs compteront.
3. **Déclare la bonne taille de famille.** Si tu testes `k` hypothèses sur le même phénomène, la correction
   doit porter sur `k`, sinon tu réintroduis la comparaison multiple qu'on cherche à éviter.
4. **Ajoute un test** en créant une entrée dans `src/loto_research/analysis/catalog.py`, avec ses tests
   unitaires, puis ouvre une *pull request* (modèle d'issue « proposition d'hypothèse » : H0, H1, test, correction).
5. Une idée née en regardant les données est `POST_HOC` : elle se teste sur des tirages futurs, jamais sur
   ceux qui l'ont suggérée.

## 8. Références dans le dépôt

- `HYPOTHESES.md` : registre complet, H009 (`POST_HOC`) et son enregistrement prospectif.
- `SPEC_V2.md` §3 : règle anti-peeking.
- `reports/FINAL.md` : conclusion de l'audit v1.
- `tests/test_hypotheses.py` : tests de la règle (refus avant `n_star`, un seul essai, exploratoire jamais confirmatoire).

## Addendum du 2026-10-31 — ajout des tirages
Les commandes `loto add`, `loto add-csv` et `loto correct` existent désormais. Chaque tirage exige une source,
un seul tirage par date est accepté, et une erreur se corrige par `loto correct` (le tirage d'origine reste intact).
Les 15 tirages du 2026-09-28 au 2026-10-31 ont été ajoutés le 2026-10-31 : ils sont datés au plus tard du jour
d'enregistrement, ils n'entrent donc pas dans le décompte de H009R-2 et H009R-49 (0/2400).
`loto hypothesis list` montre l'avancement vers n_star.
