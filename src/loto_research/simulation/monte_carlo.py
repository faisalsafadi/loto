"""Moteur de simulation Monte-Carlo général (IMPLEMENTATION_SPEC §25-27), réutilisable par les
phases suivantes (Phase 7 : paires/triplets, où aucune loi exacte simple n'existe pour les
comparaisons envisagées). Un tirage simulé choisit 6 numéros distincts parmi 49 (indices 0..48),
uniformément, indépendamment d'un tirage à l'autre et d'une simulation à l'autre (H0).
"""
import time

import numpy as np


def simulate_draws(n_draws, n_simulations, seed, batch_size=200):
    """Générateur : produit n_simulations séries de n_draws tirages, par lots de `batch_size` pour
    limiter la mémoire (IMPLEMENTATION_SPEC §70). Chaque élément produit est un tableau numpy
    (batch_actuel, n_draws, 6) d'entiers 0..48. Un nouveau Generator est créé à partir de `seed` à
    chaque appel : deux appels avec le même seed produisent des résultats strictement identiques.
    """
    rng = np.random.default_rng(seed)
    done = 0
    while done < n_simulations:
        b = min(batch_size, n_simulations - done)
        keys = rng.random((b, n_draws, 49))
        yield np.argpartition(keys, 6, axis=2)[:, :, :6]
        done += b


def simulate_gaps_for_number(n_draws, n_simulations, seed, number_zero_indexed, batch_size=200, progress=True):
    """Simule n_simulations historiques et retourne TOUS les gaps intérieurs (entre deux apparitions
    consécutives) du numéro `number_zero_indexed`, concaténés sur l'ensemble des simulations — un
    échantillon Monte-Carlo de la distribution des gaps sous H0, utilisé pour VALIDER le moteur
    (comparaison à la loi géométrique exacte, voir temporal/gaps.py), pas pour tester les vraies données.
    """
    all_gaps = []
    done = 0
    t0 = time.time()
    for batch in simulate_draws(n_draws, n_simulations, seed, batch_size):
        for sim in batch:
            present = (sim == number_zero_indexed).any(axis=1)
            positions = np.nonzero(present)[0]
            if len(positions) > 1:
                all_gaps.append(np.diff(positions))
            done += 1
        if progress:
            print(f"  Simulation gaps : {done}/{n_simulations} ({time.time() - t0:.1f}s)", end="\r")
    if progress:
        print()
    return np.concatenate(all_gaps) if all_gaps else np.array([], dtype=int)
