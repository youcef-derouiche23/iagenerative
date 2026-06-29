"""
Génère les figures d'évaluation (matplotlib) à partir du jeu de cas réel.

Produit, dans evaluation/figures/ :
  - rag_comparison.png : nDCG@5 et MRR par configuration (avant/après correctif).

Usage : python -m evaluation.make_figures
"""

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.nlp_engine import NLPEngine
from evaluation.evaluate_rag import (
    rank_config, _weights, GENRES, MOODS, validate_ground_truth,
)
from evaluation.metrics import evaluate_query, average_metrics


def main():
    root = Path(__file__).resolve().parents[1]
    fig_dir = root / "evaluation" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    queries = json.loads((root / "evaluation/test_queries.json").read_text(encoding="utf-8"))["queries"]
    engine = NLPEngine()
    referentiel = engine.load_referentiel(str(root / "data/films_referentiel.csv"))
    validate_ground_truth(queries, set(referentiel["Film"]))
    emb = engine.encode_referentiel()

    configs = {"A": "Sémantique\nseule", "B": "Pondéré\n(genre buggé)", "C": "Pondéré\ncorrigé"}
    k, pool = 5, 20
    results = {c: [] for c in configs}
    for q in queries:
        u_emb = engine.encode_text(q["query"])
        sims = engine.calculate_similarity(u_emb, emb)
        cand_idx = list(np.argsort(sims)[::-1][:pool])
        gw = _weights(q.get("genre_prefs", {}), GENRES)
        mw = _weights(q.get("mood_prefs", {}), MOODS)
        for c in configs:
            ranked = rank_config(c, cand_idx, sims, referentiel, gw, mw)
            results[c].append(evaluate_query(ranked, q["relevant"], k))
    agg = {c: average_metrics(results[c]) for c in configs}

    labels = list(configs.values())
    ndcg = [agg[c][f"ndcg@{k}"] for c in configs]
    mrr = [agg[c]["mrr"] for c in configs]

    x = np.arange(len(labels))
    width = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors_n = ["#94a3b8", "#f59e0b", "#0ea5e9"]
    b1 = ax.bar(x - width / 2, ndcg, width, label=f"nDCG@{k}", color=colors_n)
    b2 = ax.bar(x + width / 2, mrr, width, label="MRR", color=colors_n, alpha=0.55, hatch="//")
    ax.set_ylabel("Score")
    ax.set_title(f"Qualité du classement RAG — {len(queries)} requêtes annotées (k={k})")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    for bars in (b1, b2):
        for r in bars:
            ax.annotate(f"{r.get_height():.2f}", (r.get_x() + r.get_width() / 2, r.get_height()),
                        ha="center", va="bottom", fontsize=8)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = fig_dir / "rag_comparison.png"
    fig.savefig(out, dpi=150)
    print(f"Figure écrite : {out}")
    print("nDCG@5 :", {c: round(agg[c][f'ndcg@{k}'], 3) for c in configs})


if __name__ == "__main__":
    main()
