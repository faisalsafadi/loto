## Résumé / Summary

(Que change cette contribution, et pourquoi ?)

## Garde-fous / Guard rails

- [ ] Les tests passent (`python -m pytest tests -q`), dont `tests/test_no_leakage.py`.
- [ ] Toute nouvelle fonctionnalité est couverte par des tests.
- [ ] Aucune donnée réelle n'est modifiée (les erreurs se corrigent avec `loto correct`).
- [ ] Toute hypothèse nouvelle a été déclarée **avant** de regarder les données (issue liée : #...), ou est marquée `POST_HOC`.
- [ ] Toute série de tests déclare sa taille et applique une correction des comparaisons multiples.
- [ ] Aucune prédiction figée n'est modifiée ; un nouveau modèle est une nouvelle hypothèse.
- [ ] Le tableau de bord reste en lecture seule hors de `dashboard/entry.py`.
- [ ] Aucun classement de numéros, aucun vocabulaire de pronostic, aucune accusation de fraude.
- [ ] Aucun document sous droits d'auteur (PDF, etc.) n'est ajouté.
