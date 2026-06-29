"""
Métriques d'évaluation du retrieval / ranking (RAG).

Métriques standard de recherche d'information, calculées par rapport à une
vérité terrain (ensemble de films pertinents par requête) :
- Precision@k : proportion de pertinents parmi les k premiers.
- Recall@k    : proportion des pertinents retrouvés dans les k premiers.
- MRR         : Mean Reciprocal Rank (rang du 1er résultat pertinent).
- nDCG@k      : qualité du classement (pénalise les pertinents mal classés).

Aucune dépendance externe : utilisable hors ligne, sans API.
"""

from math import log2
from typing import List, Sequence


def precision_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int) -> float:
    if k == 0:
        return 0.0
    top = ranked[:k]
    rel = set(relevant)
    hits = sum(1 for x in top if x in rel)
    return hits / k


def recall_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int) -> float:
    rel = set(relevant)
    if not rel:
        return 0.0
    top = ranked[:k]
    hits = sum(1 for x in top if x in rel)
    return hits / len(rel)


def reciprocal_rank(ranked: Sequence[str], relevant: Sequence[str]) -> float:
    rel = set(relevant)
    for i, x in enumerate(ranked, start=1):
        if x in rel:
            return 1.0 / i
    return 0.0


def dcg_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int) -> float:
    rel = set(relevant)
    dcg = 0.0
    for i, x in enumerate(ranked[:k], start=1):
        if x in rel:
            dcg += 1.0 / log2(i + 1)
    return dcg


def ndcg_at_k(ranked: Sequence[str], relevant: Sequence[str], k: int) -> float:
    ideal = dcg_at_k(list(relevant), relevant, k)
    if ideal == 0:
        return 0.0
    return dcg_at_k(ranked, relevant, k) / ideal


def evaluate_query(ranked: Sequence[str], relevant: Sequence[str], k: int) -> dict:
    return {
        f"precision@{k}": precision_at_k(ranked, relevant, k),
        f"recall@{k}": recall_at_k(ranked, relevant, k),
        "mrr": reciprocal_rank(ranked, relevant),
        f"ndcg@{k}": ndcg_at_k(ranked, relevant, k),
    }


def average_metrics(per_query: List[dict]) -> dict:
    if not per_query:
        return {}
    keys = per_query[0].keys()
    return {key: sum(d[key] for d in per_query) / len(per_query) for key in keys}
