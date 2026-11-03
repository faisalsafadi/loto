#!/usr/bin/env python3
"""Mise à jour de HYPOTHESES.md : résolution officielle de H008 et H008-b suite au verdict de la
Phase 10 (walk-forward backtest, TEST OFFICIEL de H008). Remplacements exacts, avec vérification
stricte qu'ils ne s'appliquent qu'une seule fois (pour ne jamais modifier autre chose par erreur).
Si un remplacement ne correspond pas exactement, le script s'arrête sans rien écrire -- il ne
devine jamais une version approximative du texte à remplacer."""
from pathlib import Path

PATH = Path("HYPOTHESES.md")
text = PATH.read_text(encoding="utf-8")

replacements = [
    (
        "| Statut | UNTESTED |\n"
        "| Type | CONFIRMATORY — hypothèse centrale, prior fortement en faveur de H0 (cf. H000) |",
        "| Statut | REJECTED (H1 rejetée ; H0 confirmée hors-échantillon -- Phase 10, walk-forward "
        "expanding window, n=2655 tirages indépendants, 2026-10-06) |\n"
        "| Type | CONFIRMATORY — hypothèse centrale, prior fortement en faveur de H0 (cf. H000) |",
    ),
    (
        "Statut : UNTESTED (dépend entièrement de l'issue de H008 en Phase 10).",
        "Statut : REJECTED (résolu par H008, Phase 10, 2026-10-06). Sortie officielle retenue : "
        "« sous H0, tous les numéros sont statistiquement équiprobables ; aucun numéro ne présente "
        "de risque supérieur ou inférieur significatif à un autre. » Aucune liste de numéros "
        "favorisés ou déconseillés n'est produite.",
    ),
]

for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"ARRET : remplacement trouvé {count} fois (attendu exactement 1) pour le texte "
            f"commençant par :\n{old[:100]}\n\nAucune modification écrite. Colle-moi le contenu "
            f"actuel de HYPOTHESES.md autour de H008 pour que je corrige le script."
        )
    text = text.replace(old, new)

journal_marker = "| 2026-09-28 | A1–A4 |"
if journal_marker not in text:
    raise SystemExit("ARRET : marqueur du journal (ligne A1-A4) introuvable. Rien n'a été écrit.")

journal_new_row = (
    "| 2026-10-06 | H008, H008-b | Résolution officielle par la Phase 10 (walk-forward, n=2655 "
    "tirages, expanding window, test_no_future_features revérifié sur 20 points de contrôle) : H1 "
    "rejetée -- aucun modèle n'améliore les performances hors-échantillon ; frequency_baseline et "
    "logistic_regression sont significativement MOINS bons que baseline_random après correction de "
    "Holm (p_holm<0.05 pour les 3 comparaisons, IC bootstrap excluant 0), effet de taille "
    "négligeable (0,015%-0,098% de log loss). H008-b résolu en conséquence : sortie officielle = "
    "équiprobabilité, aucune liste de numéros favorisés/déconseillés. | Claude (responsable "
    "scientifique du projet) |\n"
)
text = text.replace(journal_marker, journal_new_row + journal_marker)

PATH.write_text(text, encoding="utf-8")
print("HYPOTHESES.md mis à jour : H008 et H008-b -> REJECTED. Entrée de journal ajoutée (2026-10-06).")
