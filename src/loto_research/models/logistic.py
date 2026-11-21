"""Régression logistique (IMPLEMENTATION_SPEC §33, 3e modèle après les deux baselines).
Hyperparamètres par défaut de scikit-learn (C=1.0), PAS de recherche d'hyperparamètre à ce stade
(IMPLEMENTATION_SPEC §34 impose TimeSeriesSplit/walk-forward pour tout tuning — reporté si ce
modèle justifie l'effort, amendement A9)."""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    "freq_last_10", "freq_last_20", "freq_last_50", "freq_last_100", "freq_last_250",
    "gap_current_adjusted", "prev_sum", "prev_odd_count", "prev_low_count", "prev_overlap",
]


def prepare_features(feats_df):
    """Prétraitement pré-enregistré (décidé AVANT toute évaluation, non ajusté sur les résultats,
    amendement A9) :
    - gap_current == -1 (jamais vu avant t) remplacé par (chronological_id - 1), c'est-à-dire le
      nombre maximal de tirages passés possible à cet instant — sémantiquement « aussi en retard
      que possible compte tenu de l'historique disponible », au lieu de -1 qui serait lu à tort par
      un modèle linéaire comme un écart très COURT.
    - prev_sum / prev_odd_count / prev_low_count / prev_overlap restent NaN pour les tout premiers
      tirages (absence de tirage précédent) : imputés par la moyenne du TRAIN uniquement, dans
      fit_and_predict (pas ici), pour préserver l'étanchéité train/test."""
    d = feats_df.copy()
    d["gap_current_adjusted"] = np.where(
        d["gap_current"] == -1, d["chronological_id"] - 1, d["gap_current"]
    )
    return d


def fit_and_predict(train_df, test_df, feature_columns=FEATURE_COLUMNS):
    """Ajuste sur train_df UNIQUEMENT, prédit sur test_df. Imputation (moyenne) et
    standardisation ajustées sur train UNIQUEMENT puis appliquées à test (aucune statistique de
    test n'entre dans le prétraitement)."""
    train_means = train_df[feature_columns].mean()
    X_train = train_df[feature_columns].fillna(train_means).to_numpy()
    X_test = test_df[feature_columns].fillna(train_means).to_numpy()
    y_train = train_df["target"].to_numpy()

    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, C=1.0)
    model.fit(X_train_s, y_train)

    p_train = model.predict_proba(X_train_s)[:, 1]
    p_test = model.predict_proba(X_test_s)[:, 1]
    return model, p_train, p_test
