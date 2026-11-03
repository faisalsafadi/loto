"""Prédictions exploratoires pour le PROCHAIN tirage (Phase 11 exploratoire, EXECUTION_PLAN §11).

Trois modèles pré-enregistrés, jamais d'autres : hasard uniforme, fréquence lissée (alpha = 10) et régression
logistique (C = 1,0), exactement ceux des Phases 9 et 10 (amendements A9, A10). Statut permanent : NON VALIDÉ
(aucun modèle ne bat le hasard hors échantillon, H008).

Absence de fuite : le tirage à prédire est représenté par une ligne FICTIVE ajoutée à la fin de l'historique.
Toute variable au temps t n'utilise que les données d'indice < t (règle absolue, IMPLEMENTATION_SPEC §30) : le
contenu de la ligne fictive n'influence donc rien. Un test automatique le vérifie en changeant ce contenu.
"""
import hashlib
from datetime import timedelta

import numpy as np
import pandas as pd

from loto_research.features.build import build_feature_dataset
from loto_research.models.baselines import frequency_baseline_predictions, random_baseline_predictions
from loto_research.models.logistic import FEATURE_COLUMNS, fit_and_predict, prepare_features
from loto_research.validation.schema import NUMBER_COLUMNS

MODELS = ("uniform_random", "frequency", "logistic")
DRAW_WEEKDAYS = (0, 2, 5)     # lundi, mercredi, samedi : rythme observé depuis 2016, à confirmer pour chaque tirage
K, N_MAX = 6, 49


def next_draw_date(last_date, weekdays=DRAW_WEEKDAYS):
    """Prochain jour de tirage attendu, strictement après last_date."""
    d = last_date
    for _ in range(7):
        d = d + timedelta(days=1)
        if d.weekday() in weekdays:
            return d
    raise ValueError("Aucun jour de tirage dans la semaine suivante")


def previous_scheduled_date(target, weekdays=DRAW_WEEKDAYS):
    """Dernier jour de tirage attendu, strictement avant target."""
    d = target
    for _ in range(7):
        d = d - timedelta(days=1)
        if d.weekday() in weekdays:
            return d
    raise ValueError("Aucun jour de tirage dans la semaine précédente")


def random_variant(target_date, k=K, n_max=N_MAX):
    """Combinaison de contrôle : tirage au hasard dont la graine ne dépend que de la date cible
    (reproductible, impossible à re-tirer jusqu'à obtenir une combinaison qui plaît)."""
    seed = int.from_bytes(hashlib.sha256(f"random_control|{target_date}".encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    return sorted(int(x) + 1 for x in rng.choice(n_max, size=k, replace=False))


def top_k_variant(probs, k=K):
    """Les k numéros de plus forte probabilité (égalités départagées par le plus petit numéro)."""
    order = sorted(range(len(probs)), key=lambda i: (-probs[i], i))
    return sorted(i + 1 for i in order[:k])


def _with_placeholder(df, numbers):
    d = df.sort_values("chronological_id").reset_index(drop=True)
    t = int(d["chronological_id"].max()) + 1
    ph = d.iloc[[-1]].copy()
    ph["chronological_id"] = t
    for col, v in zip(NUMBER_COLUMNS, numbers):
        ph[col] = v
    ph["date"] = ph["date"] + pd.Timedelta(days=1)
    return pd.concat([d, ph], ignore_index=True), t


def predict_next(df, target_date, _placeholder=(1, 2, 3, 4, 5, 6)):
    """Probabilités par numéro (1..49) et combinaison associée, pour chacun des trois modèles.
    `df` : tirages au format du chargeur (DATASET_v001), tous antérieurs au tirage visé."""
    d_plus, t = _with_placeholder(df, _placeholder)
    feats = prepare_features(build_feature_dataset(d_plus))
    train = feats[feats["chronological_id"] < t]
    test = feats[feats["chronological_id"] == t].sort_values("number")
    _, _, p_log = fit_and_predict(train, test, feature_columns=FEATURE_COLUMNS)
    p_freq = frequency_baseline_predictions(d_plus)[-1]
    p_rand = random_baseline_predictions(1)[0]
    models = {}
    for name, p in (("uniform_random", p_rand), ("frequency", p_freq), ("logistic", p_log)):
        probs = [float(x) for x in p]
        variant = random_variant(str(target_date)) if name == "uniform_random" else top_k_variant(probs)
        models[name] = {"probabilities": probs, "variant_numbers": variant}
    return models
