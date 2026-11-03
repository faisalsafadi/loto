# Contributing / Contribuer

**English summary.** Declare your hypothesis *before* looking at the data. Never edit real data (corrections are new
rows). Add tests. No ranking of numbers, no "hot/cold" wording, no fraud accusations. One confirmatory test per
hypothesis, on later draws only.

---

## Les règles qui comptent

1. **Hypothèse déclarée avant de regarder les données.** Ouvre une issue « Proposition d'hypothèse » (H0, H1, test,
   correction, `n_star`) avant d'analyser quoi que ce soit. Une idée née en regardant les données est `POST_HOC` : elle
   se teste sur des tirages futurs, jamais sur ceux qui l'ont suggérée.
2. **Données réelles en ajout seul.** Ne modifie jamais un tirage existant ni la base. Une erreur se corrige avec
   `loto correct` (nouvelle ligne avec raison et auteur). Chaque tirage ajouté porte sa source.
3. **Comparaisons multiples.** Tout ensemble de tests doit déclarer sa taille et appliquer une correction. Aucune
   p-value brute n'est présentée seule.
4. **Aucune fuite temporelle.** Toute variable au temps t n'utilise que des données antérieures à t. Le test
   `tests/test_no_leakage.py` doit rester vert.
5. **Un test confirmatoire par hypothèse**, sur les tirages postérieurs à son enregistrement, à l'effectif `n_star`
   fixé d'avance. Avant, des résumés descriptifs seulement.
6. **Prédictions figées jamais modifiées.** Un nouveau modèle est une nouvelle hypothèse, pas une modification d'un
   modèle existant.
7. **Vocabulaire.** Pas de classement de numéros, pas de « chaud » ni « froid », pas d'accusation de fraude : les
   sorties possibles sont « aucune anomalie détectée », « anomalie statistique » ou « anomalie robuste nécessitant une
   investigation complémentaire ». Un résultat négatif est un résultat valide.

## Technique

```bash
pip install -e ".[change-points,viz,dashboard]"
python -m pytest tests -q
```

- Toute fonction aléatoire reçoit une graine et utilise `numpy.random.Generator` (jamais le générateur global).
- Les nouvelles fonctionnalités s'accompagnent de tests. Le tableau de bord reste en lecture seule hors du module
  `dashboard/entry.py`, et un test le vérifie.
- Les PDF d'ouvrages sous droits d'auteur ne se commitent jamais.

## Pull requests

Utilise le modèle de pull request (cases à cocher). Les relecteurs vérifient d'abord les règles ci-dessus, ensuite le code.
