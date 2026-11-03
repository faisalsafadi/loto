"""test_no_future_features (IMPLEMENTATION_SPEC §36). Un échec ici est un NO-GO bloquant absolu,
sans exception (Cahier des charges, Phase 8).

Méthodologie : à un indice t choisi, on perturbe (permute) le contenu réel des tirages d'indice
>= t (le tirage t lui-même inclus), puis on reconstruit tout le dataset de features à partir de
cette version perturbée. Deux vérifications distinctes :

  - Lignes d'indice < t (strictement antérieures) : TOUTES les colonnes (features ET cible)
    doivent rester identiques. Rien de ce qui a été modifié (indices >= t) ne doit influencer
    une ligne antérieure à t — sinon une feature ou la cible dépend de données futures.

  - Ligne d'indice == t exactement : seules les colonnes de FEATURES doivent rester identiques.
    La colonne cible (target_column) est explicitement EXCLUE de cette comparaison : elle reflète
    par construction le contenu du tirage t (c'est l'étiquette à prédire, pas une feature prédictive),
    donc son changement après perturbation de t est attendu et n'est PAS une fuite. En revanche, si
    une feature change alors qu'elle ne devrait dépendre que de données < t, c'est une fuite détectée
    (notamment le cas d'une feature qui utiliserait illégitimement le contenu du tirage t lui-même,
    pas seulement une fuite "vers le futur").
"""
import numpy as np
import pandas as pd

from loto_research.validation.schema import NUMBER_COLUMNS


def test_no_future_features(df, build_fn, n_checks=10, seed=0, target_column="target"):
    """Retourne {"checkpoints_tested": [...], "failures": [...], "passed": bool}."""
    rng = np.random.default_rng(seed)
    full = build_fn(df)
    n_draws = int(df["chronological_id"].max())
    low = min(10, max(2, n_draws // 10))
    if n_draws <= low:
        checkpoints = np.array([n_draws // 2]) if n_draws > 1 else np.array([], dtype=int)
    else:
        size = min(n_checks, n_draws - low)
        checkpoints = rng.choice(np.arange(low, n_draws), size=size, replace=False)

    failures = []
    for t in checkpoints:
        df_perturbed = df.copy()
        future_idx = df_perturbed.index[df_perturbed["chronological_id"] >= t]
        permuted_idx = rng.permutation(future_idx)
        for col in NUMBER_COLUMNS + ["bonus"]:
            if col in df_perturbed.columns:
                df_perturbed.loc[future_idx, col] = df.loc[permuted_idx, col].to_numpy()

        perturbed = build_fn(df_perturbed)

        # Lignes strictement antérieures à t : tout doit être identique (features ET cible).
        before_full = full[full["chronological_id"] < t].reset_index(drop=True)
        before_perturbed = perturbed[perturbed["chronological_id"] < t].reset_index(drop=True)
        if not before_full.equals(before_perturbed):
            failures.append(int(t))
            continue

        # Ligne t elle-même : seules les features doivent être identiques, pas la cible.
        at_full = full[full["chronological_id"] == t].reset_index(drop=True)
        at_perturbed = perturbed[perturbed["chronological_id"] == t].reset_index(drop=True)
        compare_cols = [c for c in at_full.columns if c != target_column]
        if not at_full[compare_cols].equals(at_perturbed[compare_cols]):
            failures.append(int(t))

    return {
        "checkpoints_tested": [int(x) for x in checkpoints],
        "failures": failures,
        "passed": len(failures) == 0,
    }


# Empêche pytest de collecter cette fonction comme un test lorsqu'elle est importée ailleurs
# (son nom est imposé par IMPLEMENTATION_SPEC §36 et commence par "test_").
test_no_future_features.__test__ = False
