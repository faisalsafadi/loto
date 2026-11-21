"""Génération du DATA_QUALITY_REPORT.md (Cahier des charges §9)."""
from collections import Counter

from loto_research.validation.schema import NUMBER_COLUMNS


def build_report(header, n_empty, records, invalid_df, all_dup_df, removed_df, analytic_df, expected_rows):
    n_raw = len(records)
    flags_flat = [f for row in analytic_df["flags"] for f in (row.split(";") if row else []) if f]
    flag_kinds = Counter(f.split(":")[0] for f in flags_flat)
    bonus_in_main = flag_kinds.get("BONUS_IN_MAIN", 0)
    n_final = len(analytic_df)
    rate = bonus_in_main / n_final if n_final else float("nan")

    lines = [
        "# DATA_QUALITY_REPORT.md",
        "",
        "## LOTO MAROC Research Engine — Rapport qualité (Phase 2)",
        "",
        "Généré automatiquement. Aucune valeur n'a été corrigée ; toute anomalie est",
        "signalée (flag) ou exportée (invalid_records.csv / duplicate_dates.csv), jamais supprimée silencieusement.",
        "",
        "## OBSERVATION",
        f"- Lignes de données dans le RAW (hors en-tête, hors lignes entièrement vides) : {n_raw}",
        f"- Lignes entièrement vides ignorées : {n_empty}",
        f"- Nombre de tirages attendu (Cahier des charges) : {expected_rows}",
        f"- Écart RAW vs attendu : {n_raw - expected_rows:+d} (voir PHASE_1_REPORT.md — accepté formellement par l'utilisateur le 2026-09-28)",
        f"- Lignes invalides (V001–V005) : {len(invalid_df)}",
        f"- Lignes concernées par une date dupliquée : {len(all_dup_df)} ; supprimées de l'ANALYTIC (keep first) : {len(removed_df)}",
        f"- Lignes dans le dataset ANALYTIC final : {n_final}",
        f"- Première date : {analytic_df['date'].min().date() if n_final else 'N/A'}",
        f"- Dernière date : {analytic_df['date'].max().date() if n_final else 'N/A'}",
        f"- Années représentées : {sorted(analytic_df['year'].unique().tolist()) if n_final else []}",
        "",
        "## CALCUL — répartition des lignes invalides par règle",
    ]
    if len(invalid_df):
        by_rule = Counter(r for rules in invalid_df["validation_rule"] for r in rules.split(";"))
        for rule, n in sorted(by_rule.items()):
            lines.append(f"- {rule} : {n}")
    else:
        lines.append("- Aucune ligne invalide détectée (0 ligne V001–V005).")

    lines += [
        "",
        "## CALCUL — signalements non bloquants (flags), dataset ANALYTIC",
        f"- Total de signalements : {len(flags_flat)}",
    ]
    for kind, n in sorted(flag_kinds.items(), key=lambda x: -x[1]):
        lines.append(f"- {kind} : {n}")

    lines += [
        "",
        "## INTERPRÉTATION — règle du numéro complémentaire (Cahier §6, H002)",
        f"- BONUS_IN_MAIN (complémentaire == un des 6 principaux) : {bonus_in_main} / {n_final} tirages ({rate:.2%})",
        "- Aucune source officielle trouvée (RESEARCH_REVIEW.md) ne précise explicitement si le complémentaire",
        "  est tiré parmi les 43 numéros restants ou indépendamment parmi les 49.",
        "- Règle de décision, fixée AVANT ce calcul (non post-hoc) :",
        "    taux observé ≈ 0 %  -> complémentaire exclusif des 6 principaux (tirage sans remise étendu) ;",
        "    taux observé ≈ 12,24 % (6/49) -> tirage du complémentaire indépendant, avec remise possible.",
        "    tout taux intermédiaire reproductible -> anomalie à investiguer (Phase 4), pas une règle du jeu.",
        "",
        "## LIMITATION",
        "- Le fichier source a été modifié par l'utilisateur avant import (voir PHASE_1_REPORT.md) ; les",
        "  modifications ne sont pas documentées. Le RAW n'est donc pas la sortie brute originale du site.",
        "- Les tirages numérotés mais absents (~42, cf. diagnostic Phase 1) ne sont ni comptés comme invalides",
        "  ni reconstitués : ils sont simplement absents du dataset, ce qui affecte H003/H004 (voir amendement A5).",
        "- draw_number_source n'est PAS un identifiant global (numérotation remise à zéro plusieurs fois,",
        "  cf. diagnostic Phase 1) : chronological_id et draw_id en tiennent lieu (IMPLEMENTATION_SPEC §7).",
    ]
    return "\n".join(lines) + "\n"
