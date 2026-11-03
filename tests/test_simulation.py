import numpy as np
import pytest

from loto_research.simulation.monte_carlo import simulate_draws, simulate_gaps_for_number


def test_simulate_draws_shape_range_and_distinctness():
    batches = list(simulate_draws(n_draws=10, n_simulations=5, seed=1, batch_size=2))
    total = sum(b.shape[0] for b in batches)
    assert total == 5
    for b in batches:
        assert b.shape[1:] == (10, 6)
        assert b.min() >= 0 and b.max() <= 48
        for sim in b:
            for draw in sim:
                assert len(set(draw.tolist())) == 6  # 6 numeros distincts par tirage


def test_simulate_draws_reproducible_with_same_seed():
    a = list(simulate_draws(n_draws=20, n_simulations=10, seed=7, batch_size=4))
    b = list(simulate_draws(n_draws=20, n_simulations=10, seed=7, batch_size=4))
    for ba, bb in zip(a, b):
        np.testing.assert_array_equal(ba, bb)


def test_simulate_draws_different_seeds_give_different_results():
    a = np.concatenate(list(simulate_draws(n_draws=20, n_simulations=10, seed=1)))
    b = np.concatenate(list(simulate_draws(n_draws=20, n_simulations=10, seed=2)))
    assert not np.array_equal(a, b)


def test_simulate_gaps_for_number_matches_geometric_mean_approximately():
    p = 6 / 49
    gaps = simulate_gaps_for_number(n_draws=3000, n_simulations=300, seed=42,
                                     number_zero_indexed=0, progress=False)
    assert len(gaps) > 1000
    assert gaps.mean() == pytest.approx(1 / p, rel=0.1)
