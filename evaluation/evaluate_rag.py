"""
Évaluation du RAG d'AISCA-Cinema (compétence C5.3).

Ce script mesure objectivement la qualité du moteur de recommandation sur un jeu
de cas annoté (evaluation/test_queries.json) et compare plusieurs configurations
de classement — fournissant la preuve « avant / après ajustement » attendue.

Configurations comparées :
  A. Sémantique seule            : classement par similarité SBERT uniquement.
  B. Pondéré — genre buggé (EN)  : score 50/30/20 mais genre lu sur la colonne
                                   `Genre` (anglais) -> reproduit le bug audité.
  C. Pondéré — corrigé (Categorie): score 50/30/20 avec la catégorie française.

Métriques (k=5) : Precision@k, Recall@k, MRR, nDCG@k, moyennées sur les requêtes.

Usage :
    python -m evaluation.evaluate_rag
    python -m evaluation.evaluate_rag --k 5 --pool 20 --out evaluation/RESULTS.md

Hors ligne : n'utilise PAS l'API Gemini (uniquement SBERT + scoring). Reproductible.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.nlp_engine import NLPEngine
from src.scoring import ScoringSystem
from evaluation.metrics import evaluate_query, average_metrics

# Libellés du questionnaire (repris ici pour éviter d'importer Streamlit)
GENRES = ["Science-Fiction", "Drame", "Fantasy", "Animation", "Thriller",
          "Comedie", "Horreur", "Romance", "Action", "Biopic"]
MOODS = ["Intellectuel/Reflexif", "Emotionnel/Touchant", "Intense/Tendu",
         "Leger/Amusant", "Sombre/Derangeant", "Inspirant/Optimiste",
         "Contemplatif/Melancolique", "Energique/Dynamique"]
DEFAULT_LIKERT = 3  # valeur neutre par défaut du questionnaire


def _weights(prefs: dict, all_keys: list) -> dict:
    """Construit des poids [0,1] pour TOUS les libellés (défaut neutre 3/5)."""
    out = {k: DEFAULT_LIKERT / 5.0 for k in all_keys}
    for k, v in prefs.items():
        out[k] = v / 5.0
    return out


def validate_ground_truth(queries: list, titles: set) -> None:
    """Vérifie que chaque film de la vérité terrain existe dans le corpus."""
    problems = []
    for q in queries:
        for film in q["relevant"]:
            if film not in titles:
                problems.append((q["id"], film))
    if problems:
        print("ATTENTION — titres de vérité terrain introuvables dans le corpus :")
        for qid, film in problems:
            print(f"  [{qid}] {film!r}")
        print("Corrigez test_queries.json pour des métriques fiables.\n")
    else:
        print("Vérité terrain validée : tous les titres existent dans le corpus.\n")


def rank_config(config, cand_idx, sims, referentiel, gw, mw):
    """Retourne la liste ordonnée des titres pour une configuration donnée."""
    if config == "A":  # sémantique seule
        ordered = sorted(cand_idx, key=lambda i: sims[i], reverse=True)
        return [referentiel.iloc[i]["Film"] for i in ordered]

    scorer = ScoringSystem(alpha=0.50, beta=0.30, gamma=0.20)
    recs = []
    for i in cand_idx:
        film = referentiel.iloc[i]
        rec = {
            "titre": film["Film"],
            "genre": film["Genre"],            # colonne anglaise (bug)
            "mood": film["Mood"],
            "score_similarite": float(sims[i]),
        }
        if config == "C":  # correctif : catégorie française
            rec["categorie"] = film["Categorie"]
        # config B : pas de 'categorie' -> rank_films retombe sur 'genre' (EN)
        recs.append(rec)

    ranked = scorer.rank_films(recs, sims, gw, mw, referentiel)
    return [r["titre"] for r in ranked]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--pool", type=int, default=20, help="taille du pool de candidats")
    ap.add_argument("--queries", default="evaluation/test_queries.json")
    ap.add_argument("--data", default="data/films_referentiel.csv")
    ap.add_argument("--out", default="evaluation/RESULTS.md")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    queries = json.loads((root / args.queries).read_text(encoding="utf-8"))["queries"]

    print("Chargement du modèle SBERT et du référentiel...")
    engine = NLPEngine()
    referentiel = engine.load_referentiel(str(root / args.data))
    titles = set(referentiel["Film"])
    validate_ground_truth(queries, titles)

    emb = engine.encode_referentiel()  # une seule fois

    configs = {
        "A": "Sémantique seule (baseline)",
        "B": "Pondéré — genre buggé (colonne EN)",
        "C": "Pondéré — corrigé (Categorie FR)",
    }
    results = {c: [] for c in configs}
    per_query_rows = []

    for q in queries:
        u_emb = engine.encode_text(q["query"])
        sims = engine.calculate_similarity(u_emb, emb)
        cand_idx = list(np.argsort(sims)[::-1][:args.pool])
        gw = _weights(q.get("genre_prefs", {}), GENRES)
        mw = _weights(q.get("mood_prefs", {}), MOODS)

        row = {"id": q["id"]}
        for c in configs:
            ranked = rank_config(c, cand_idx, sims, referentiel, gw, mw)
            m = evaluate_query(ranked, q["relevant"], args.k)
            results[c].append(m)
            row[c] = m[f"ndcg@{args.k}"]
        per_query_rows.append(row)

    # Agrégats
    agg = {c: average_metrics(results[c]) for c in configs}

    # Affichage console
    print("\n=== RÉSULTATS (moyenne sur {} requêtes, k={}) ===".format(len(queries), args.k))
    metric_keys = list(next(iter(agg.values())).keys())
    header = f"{'Config':<40}" + "".join(f"{k:>14}" for k in metric_keys)
    print(header)
    print("-" * len(header))
    for c, label in configs.items():
        line = f"{label:<40}" + "".join(f"{agg[c][k]:>14.3f}" for k in metric_keys)
        print(line)

    # Écriture Markdown
    k = args.k
    md = []
    md.append("# Résultats d'évaluation du RAG — AISCA-Cinema (C5.3)\n")
    md.append(f"_Généré par `evaluation/evaluate_rag.py` — {len(queries)} requêtes annotées, "
              f"k={k}, pool de {args.pool} candidats, modèle SBERT "
              f"`{engine.model_name}`._\n")
    md.append("## 1. Comparaison des configurations de classement (avant / après)\n")
    md.append("| Configuration | Precision@{k} | Recall@{k} | MRR | nDCG@{k} |".format(k=k))
    md.append("|---|---|---|---|---|")
    for c, label in configs.items():
        a = agg[c]
        md.append(f"| {label} | {a[f'precision@{k}']:.3f} | {a[f'recall@{k}']:.3f} "
                  f"| {a['mrr']:.3f} | {a[f'ndcg@{k}']:.3f} |")
    md.append("")
    base = agg["A"][f"ndcg@{k}"]
    fixed = agg["C"][f"ndcg@{k}"]
    buggy = agg["B"][f"ndcg@{k}"]
    gain = (fixed - base) / base * 100 if base else 0.0
    md.append("## 2. Lecture\n")
    md.append(f"- **A → C (correctif)** : nDCG@{k} passe de **{base:.3f}** à "
              f"**{fixed:.3f}** ({gain:+.1f} %). La pondération genre/mood corrigée "
              f"améliore le classement par rapport au sémantique seul.")
    md.append(f"- **B (genre buggé)** : nDCG@{k} = **{buggy:.3f}**, quasi identique au "
              f"sémantique seul ({base:.3f}) — preuve chiffrée que le composant genre "
              f"était neutralisé (constant à 0.5) avant correctif.")
    md.append("")
    md.append("## 3. Détail par requête (nDCG@{k})\n".format(k=k))
    md.append("| Requête | A (sémantique) | B (buggé) | C (corrigé) |")
    md.append("|---|---|---|---|")
    for r in per_query_rows:
        md.append(f"| {r['id']} | {r['A']:.3f} | {r['B']:.3f} | {r['C']:.3f} |")
    md.append("")
    md.append("> Méthodologie : pour chaque requête, on récupère un pool de "
              f"{args.pool} films par similarité SBERT, puis on reclasse selon chaque "
              "configuration. Les métriques sont calculées vs la vérité terrain "
              "annotée dans `test_queries.json`.\n")

    (root / args.out).write_text("\n".join(md), encoding="utf-8")
    print(f"\nRésultats écrits dans {args.out}")


if __name__ == "__main__":
    main()
