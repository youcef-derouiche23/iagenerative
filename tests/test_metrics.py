"""Tests des métriques d'évaluation (retrieval)."""

import math
import pytest

from evaluation.metrics import (
    precision_at_k, recall_at_k, reciprocal_rank, ndcg_at_k, evaluate_query,
    average_metrics,
)

RANKED = ["a", "b", "c", "d", "e"]
RELEVANT = ["b", "d"]


def test_precision_at_k():
    assert precision_at_k(RANKED, RELEVANT, 5) == pytest.approx(2 / 5)
    assert precision_at_k(RANKED, RELEVANT, 2) == pytest.approx(1 / 2)


def test_recall_at_k():
    assert recall_at_k(RANKED, RELEVANT, 5) == pytest.approx(1.0)
    assert recall_at_k(RANKED, RELEVANT, 2) == pytest.approx(0.5)


def test_mrr_premier_pertinent_rang_2():
    assert reciprocal_rank(RANKED, RELEVANT) == pytest.approx(0.5)
    assert reciprocal_rank(["b", "a"], RELEVANT) == pytest.approx(1.0)
    assert reciprocal_rank(["x", "y"], RELEVANT) == 0.0


def test_ndcg_parfait_vaut_1():
    # Classement idéal -> nDCG = 1
    assert ndcg_at_k(["b", "d", "a"], RELEVANT, 3) == pytest.approx(1.0)


def test_ndcg_valeur_connue():
    # b en pos2, d en pos4 -> dcg/idcg calculés à la main
    dcg = 1 / math.log2(3) + 1 / math.log2(5)
    idcg = 1 / math.log2(2) + 1 / math.log2(3)
    assert ndcg_at_k(RANKED, RELEVANT, 5) == pytest.approx(dcg / idcg)


def test_evaluate_query_keys():
    m = evaluate_query(RANKED, RELEVANT, 5)
    assert set(m) == {"precision@5", "recall@5", "mrr", "ndcg@5"}


def test_average_metrics():
    a = {"x": 1.0, "y": 0.0}
    b = {"x": 0.0, "y": 1.0}
    avg = average_metrics([a, b])
    assert avg["x"] == pytest.approx(0.5) and avg["y"] == pytest.approx(0.5)


def test_relevant_vide_ne_crashe_pas():
    assert recall_at_k(RANKED, [], 5) == 0.0
    assert ndcg_at_k(RANKED, [], 5) == 0.0
