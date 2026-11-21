import pytest

from loto_research.statistics.multiple_testing import bonferroni, fdr_bh, holm


def test_bonferroni_adjusts_by_number_of_tests():
    res = bonferroni([0.01, 0.02, 0.5], alpha=0.05)
    assert res["number_of_tests"] == 3
    assert res["adjusted_p_value"][0] == pytest.approx(min(1.0, 0.01 * 3))
    assert res["method"] == "bonferroni"


def test_holm_at_least_as_powerful_as_bonferroni():
    pvals = [0.001, 0.002, 0.5, 0.6, 0.7]
    b = bonferroni(pvals)
    h = holm(pvals)
    assert all(h_adj <= b_adj + 1e-12 for h_adj, b_adj in zip(h["adjusted_p_value"], b["adjusted_p_value"]))


def test_fdr_bh_rejects_all_when_all_pvalues_tiny():
    res = fdr_bh([0.001] * 5, alpha=0.05)
    assert all(res["reject"])


def test_no_rejection_when_all_pvalues_large():
    for fn in (bonferroni, holm, fdr_bh):
        res = fn([0.4, 0.5, 0.6, 0.7], alpha=0.05)
        assert not any(res["reject"])


def test_number_of_tests_and_raw_pvalues_preserved():
    pvals = [0.01, 0.2, 0.03]
    res = holm(pvals)
    assert res["number_of_tests"] == 3
    assert res["raw_p_value"] == pvals
