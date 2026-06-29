"""
Comparaison « avant / après » des paramètres de génération LLM (C5.3).

Génère le profil cinéphile pour quelques cas du jeu d'évaluation sous deux
configurations de paramètres (Factuelle vs Créative) et calcule des indicateurs
automatiques objectifs pour alimenter la grille d'évaluation
(evaluation/evaluation_grid.md) :
  - longueur (mots),
  - diversité lexicale (type-token ratio),
  - respect du format (présence de Markdown / longueur cible),
  - mentions de films HORS référentiel (proxy d'hallucination).

Nécessite une clé API Gemini (GEMINI_API_KEY dans .env). Sans clé, le script
explique la méthodologie et s'arrête proprement (il ne plante pas).

Usage :
    python -m evaluation.compare_params --cases Q01 Q04 Q09 --out evaluation/params_results.md
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.nlp_engine import NLPEngine
from src.scoring import ScoringSystem

CONFIGS = {
    "Factuelle": {"temperature": 0.2, "top_p": 0.8, "top_k": 40, "max_output_tokens": 1024},
    "Créative": {"temperature": 0.9, "top_p": 0.95, "top_k": 40, "max_output_tokens": 1024},
}

GENRES = ["Science-Fiction", "Drame", "Fantasy", "Animation", "Thriller",
          "Comedie", "Horreur", "Romance", "Action", "Biopic"]
MOODS = ["Intellectuel/Reflexif", "Emotionnel/Touchant", "Intense/Tendu",
         "Leger/Amusant", "Sombre/Derangeant", "Inspirant/Optimiste",
         "Contemplatif/Melancolique", "Energique/Dynamique"]


def _weights(prefs, keys):
    out = {k: 0.6 for k in keys}
    for k, v in prefs.items():
        out[k] = v / 5.0
    return out


def lexical_diversity(text: str) -> float:
    words = re.findall(r"\w+", text.lower())
    return len(set(words)) / len(words) if words else 0.0


def count_offcorpus_titles(text: str, corpus_titles: set) -> int:
    """Compte les titres entre guillemets/markdown absents du référentiel (proxy)."""
    candidates = re.findall(r'[«"*]([A-ZÀ-Ý][^«»"*\n]{2,60})[»"*]', text)
    off = 0
    for c in candidates:
        c = c.strip(" .,:;")
        if not c:
            continue
        if not any(c.lower() in t.lower() or t.lower() in c.lower() for t in corpus_titles):
            off += 1
    return off


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="+", default=["Q01", "Q04", "Q09"])
    ap.add_argument("--queries", default="evaluation/test_queries.json")
    ap.add_argument("--data", default="data/films_referentiel.csv")
    ap.add_argument("--out", default="evaluation/params_results.md")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]

    # Vérifier la disponibilité de la clé API avant tout chargement lourd
    try:
        from src.genai_integration import GenAIIntegration, _get_api_key
    except Exception as e:  # pragma: no cover
        print(f"Import GenAI impossible : {e}")
        return
    if not _get_api_key():
        print("Aucune clé API Gemini détectée (GEMINI_API_KEY).")
        print("Méthodologie : ce script génère le profil cinéphile sous deux")
        print("configurations (Factuelle temp=0.2 / Créative temp=0.9) et mesure")
        print("longueur, diversité lexicale et titres hors-corpus (proxy")
        print("d'hallucination). Renseignez .env puis relancez pour obtenir les")
        print("chiffres réels à reporter dans la grille d'évaluation.")
        return

    queries = json.loads((root / args.queries).read_text(encoding="utf-8"))["queries"]
    by_id = {q["id"]: q for q in queries}

    print("Chargement SBERT + référentiel...")
    engine = NLPEngine()
    referentiel = engine.load_referentiel(str(root / args.data))
    corpus_titles = set(referentiel["Film"])
    emb = engine.encode_referentiel()
    scorer = ScoringSystem()

    rows = []
    for cid in args.cases:
        q = by_id[cid]
        u_emb = engine.encode_text(q["query"])
        sims = engine.calculate_similarity(u_emb, emb)
        recs, _ = engine.analyze_user_input(q["query"], top_n=3)
        gw = _weights(q.get("genre_prefs", {}), GENRES)
        mw = _weights(q.get("mood_prefs", {}), MOODS)
        ranked = scorer.rank_films(recs, sims, gw, mw, referentiel)

        for cfg_name, cfg in CONFIGS.items():
            genai = GenAIIntegration(generation_config=cfg)
            profile = genai.generate_cinephile_profile(ranked[:3], gw, mw, 0.6)
            rows.append({
                "case": cid,
                "config": cfg_name,
                "temperature": cfg["temperature"],
                "words": len(profile.split()),
                "diversity": round(lexical_diversity(profile), 3),
                "offcorpus": count_offcorpus_titles(profile, corpus_titles),
                "text": profile,
            })
            print(f"[{cid}] {cfg_name}: {rows[-1]['words']} mots, "
                  f"diversité {rows[-1]['diversity']}, hors-corpus {rows[-1]['offcorpus']}")

    md = ["# Comparaison des paramètres de génération LLM — AISCA-Cinema (C5.3)\n"]
    md.append("Indicateurs automatiques (proxys de la grille qualitative).\n")
    md.append("| Cas | Config | Température | Mots | Diversité lexicale | Titres hors-corpus (proxy hallucination) |")
    md.append("|---|---|---|---|---|---|")
    for r in rows:
        md.append(f"| {r['case']} | {r['config']} | {r['temperature']} | {r['words']} "
                  f"| {r['diversity']} | {r['offcorpus']} |")
    md.append("\n## Textes générés (pour notation manuelle sur la grille)\n")
    for r in rows:
        md.append(f"### {r['case']} — {r['config']} (temp={r['temperature']})\n")
        md.append(r["text"] + "\n")

    (root / args.out).write_text("\n".join(md), encoding="utf-8")
    print(f"\nRésultats écrits dans {args.out}")


if __name__ == "__main__":
    main()
