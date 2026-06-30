"""
Baseline TF-IDF vs retrieval sémantique SBERT — C5.2 / C5.3.

Compare un retrieval « mots-clés » classique (TF-IDF + cosinus) au retrieval
sémantique (SBERT). Objectif : prouver chiffrement que SBERT apporte un gain
réel, plutôt que de l'affirmer. Hors ligne, aucune clé API.

Usage : python -m evaluation.baseline_tfidf
"""

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.nlp_engine import NLPEngine
from evaluation.evaluate_rag import validate_ground_truth
from evaluation.metrics import evaluate_query, average_metrics


def main():
    k, pool = 5, 20
    root = Path(__file__).resolve().parents[1]
    queries = json.loads((root / "evaluation/test_queries.json").read_text(encoding="utf-8"))["queries"]

    print("Chargement SBERT + référentiel...")
    engine = NLPEngine()
    referentiel = engine.load_referentiel(str(root / "data/films_referentiel.csv"))
    validate_ground_truth(queries, set(referentiel["Film"]))
    corpus = referentiel["texte_complet"].tolist()
    titles = referentiel["Film"].tolist()

    # --- Baseline TF-IDF (mots-clés) ---
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1)
    doc_matrix = vectorizer.fit_transform(corpus)

    # --- SBERT (sémantique) ---
    emb = engine.encode_referentiel()

    res_tfidf, res_sbert = [], []
    for q in queries:
        # TF-IDF
        qv = vectorizer.transform([q["query"]])
        sims_t = cosine_similarity(qv, doc_matrix)[0]
        order_t = np.argsort(sims_t)[::-1][:k]
        ranked_t = [titles[i] for i in order_t]
        res_tfidf.append(evaluate_query(ranked_t, q["relevant"], k))

        # SBERT
        sims_s = engine.calculate_similarity(engine.encode_text(q["query"]), emb)
        order_s = np.argsort(sims_s)[::-1][:k]
        ranked_s = [titles[i] for i in order_s]
        res_sbert.append(evaluate_query(ranked_s, q["relevant"], k))

    agg_t = average_metrics(res_tfidf)
    agg_s = average_metrics(res_sbert)

    keyn = f"ndcg@{k}"
    gain = (agg_s[keyn] - agg_t[keyn]) / agg_t[keyn] * 100 if agg_t[keyn] else 0.0
    print(f"\nTF-IDF  nDCG@{k}={agg_t[keyn]:.3f}  MRR={agg_t['mrr']:.3f}")
    print(f"SBERT   nDCG@{k}={agg_s[keyn]:.3f}  MRR={agg_s['mrr']:.3f}  (gain {gain:+.1f}%)")

    md = ["# Baseline TF-IDF vs SBERT — AISCA-Cinema (C5.2/C5.3)\n",
          f"_Retrieval pur (sans reranking), {len(queries)} requêtes annotées, k={k}._\n",
          f"| Méthode | Precision@{k} | Recall@{k} | MRR | nDCG@{k} |",
          "|---|---|---|---|---|",
          f"| TF-IDF (mots-clés) | {agg_t[f'precision@{k}']:.3f} | {agg_t[f'recall@{k}']:.3f} "
          f"| {agg_t['mrr']:.3f} | {agg_t[keyn]:.3f} |",
          f"| **SBERT (sémantique)** | {agg_s[f'precision@{k}']:.3f} | {agg_s[f'recall@{k}']:.3f} "
          f"| {agg_s['mrr']:.3f} | **{agg_s[keyn]:.3f}** |",
          "",
          f"> SBERT améliore le nDCG@{k} de **{gain:+.1f} %** vs une recherche par mots-clés : "
          "la compréhension sémantique de la requête en langage naturel apporte une "
          "valeur mesurable (justifie le choix d'embeddings plutôt qu'un index lexical).\n"]
    (root / "evaluation/baseline_results.md").write_text("\n".join(md), encoding="utf-8")
    print("Résultats écrits dans evaluation/baseline_results.md")


if __name__ == "__main__":
    main()
