# AISCA-Cinema — Agent de recommandation cinématographique (RAG)

**Auteurs** : Anthony BOUCHER & Youcef DEROUICHE
**Module** : IA Générative — EFREI 2025-2026 (Bloc 2)
**Certification** : RNCP40875 — Expert en Ingénierie des données (compétences C5.1 → C5.3)

---

## 1. Besoin métier

Face à une offre de films pléthorique, choisir quoi regarder est coûteux en temps
et frustrant : les moteurs par mots-clés ne comprennent pas une envie exprimée en
langage naturel (« un film contemplatif sur la mémoire »). **AISCA-Cinema** répond
à ce besoin de **découverte personnalisée** : l'utilisateur décrit son envie avec
ses mots, et l'agent recommande des films pertinents **et explique pourquoi**, en
s'appuyant sur un référentiel maîtrisé (pas d'invention).

Pourquoi la **GenAI** ici (et pas une reco classique seule) : la valeur ajoutée
est la **compréhension sémantique** de la demande (SBERT) + une **restitution en
langage naturel** personnalisée et pédagogique (LLM) — ce qu'un filtre par genres
ne sait pas faire.

## 2. Approche : un RAG (Retrieval-Augmented Generation)

```
Questionnaire ──► SBERT (embeddings) ──► similarité cosinus ──► Top films (Retrieval)
                                                                     │
                          Scoring pondéré (sémantique/genre/mood) ◄──┘
                                                                     │
                                         Gemini (Generation) ◄── contexte = films récupérés
                                                                     │
                                     Profil cinéphile + Plan de découverte (ancrés sur les sources)
```

- **Retrieval** : `paraphrase-multilingual-MiniLM-L12-v2` (SBERT multilingue) +
  similarité cosinus sur 260 films.
- **Ranking** : score pondéré `0.50 × sémantique + 0.40 × genre + 0.10 × mood`
  (poids **calibrés par validation croisée**, cf. `evaluation/tune_weights.py`).
- **Generation** : Google **Gemini** (`gemini-2.5-flash`) rédige le profil et le
  plan, **uniquement à partir des films récupérés** (garde-fou anti-hallucination),
  avec retry/backoff sur quota, `safety_settings` et anti-prompt-injection.

**Pourquoi RAG plutôt que fine-tuning ou prompting seul** : le corpus de films
évolue sans réentraînement, la génération reste **traçable** (sources = films
récupérés), et le coût est maîtrisé (pas d'entraînement, cache des appels LLM).

## 3. Installation

Prérequis : **Python 3.11**, une clé **Google Gemini** (gratuite via
[Google AI Studio](https://aistudio.google.com/app/apikey)).

```bash
# 1. Environnement virtuel
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate

# 2. Dépendances
pip install -r requirements.txt
# Astuce : pour une installation plus légère sans GPU,
#   pip install torch --index-url https://download.pytorch.org/whl/cpu
#   puis pip install -r requirements.txt

# 3. Configuration
cp .env.example .env               # puis renseignez votre GEMINI_API_KEY
```

> ⚠️ **Sécurité** : ne committez jamais votre `.env` (déjà gitignoré). Le
> `.env.example` ne contient qu'un *placeholder*.

## 4. Lancement

```bash
streamlit run app.py
```

L'application s'ouvre dans le navigateur. Parcours en 4 étapes : **questionnaire →
analyse sémantique → scoring → génération** (profil + plan).

### Exemple d'entrée / sortie

- **Entrée** (description libre) : *« Un film de science-fiction philosophique sur
  le temps et la mémoire, visuellement spectaculaire. »* + genres SF=5, Drame=4.
- **Sortie** (Top 3 récupéré, vérifié) : *Interstellar*, *Inception*, *The Matrix*
  (+ profil cinéphile et plan de découverte générés et ancrés sur ces films).

## 5. Évaluation de la qualité (C5.3)

Le dossier [`evaluation/`](evaluation/) contient un cadre d'évaluation reproductible.

```bash
# Évaluation quantitative du RAG (hors ligne, sans API) -> evaluation/RESULTS.md :
python -m evaluation.evaluate_rag

# Calibrage des poids par validation croisée -> evaluation/weights_tuning.md :
python -m evaluation.tune_weights

# Baseline TF-IDF vs SBERT (apport du sémantique) -> evaluation/baseline_results.md :
python -m evaluation.baseline_tfidf

# Figure de comparaison (matplotlib) -> evaluation/figures/rag_comparison.png :
python -m evaluation.make_figures

# Comparaison des paramètres LLM + LLM-as-judge (nécessite une clé API) :
python -m evaluation.compare_params --cases Q01 Q04 Q09
```

- **Jeu de cas** : `evaluation/test_queries.json` — 15 requêtes annotées (vérité terrain).
- **Métriques** : Precision@k, Recall@k, MRR, nDCG@k (`evaluation/metrics.py`).
- **Calibrage des poids** : grid-search → 50/40/10 (`tune_weights.py`).
- **Baseline** : TF-IDF vs SBERT (`baseline_tfidf.py`).
- **Qualité de génération** : LLM-as-judge (pertinence, exactitude, hallucination,
  ton) + comparaison de température (`compare_params.py`).
- **Résultat clé** : le correctif + calibrage du scoring fait passer le **nDCG@5
  de 0.333 à 0.506 (+52 %)** et le **MRR de 0.59 à 0.78** ; SBERT bat une baseline
  TF-IDF de **+961 %** (requêtes FR / corpus EN).

### Tests

```bash
pip install pytest
pytest -q
```

## 6. Structure du projet

```
app.py                       # UI Streamlit (orchestration)
data/films_referentiel.csv   # corpus RAG : 260 films
src/questionnaire.py         # collecte & structuration des préférences
src/nlp_engine.py            # SBERT : embeddings + retrieval (+ cache embeddings)
src/scoring.py               # score pondéré sémantique/genre/mood
src/genai_integration.py     # Gemini : génération + GenerationConfig + cache
src/cache_manager.py         # cache disque des réponses LLM
src/visualization.py         # graphiques Plotly
evaluation/                  # jeu de cas, métriques, scripts d'évaluation
scripts/                     # captures d'écran (Playwright), génération des livrables
tests/                       # tests unitaires (pytest)
Dockerfile                   # conteneurisation (Streamlit, torch CPU)
```

> Les livrables rédigés (rapport, slides, plan de soutenance, antisèche, dossier
> d'audit) ne sont pas versionnés : ils sont générés au format Office par
> `python scripts/generate_deliverables.py` (dossier `livrables/`, gitignoré).

## 5 bis. Conteneurisation (Docker)

```bash
docker build -t aisca-cinema .
docker run -p 8501:8501 --env-file .env aisca-cinema
```

## 5 ter. Mode dégradé (résilience)

Sans clé API Gemini, l'application reste utilisable : le cœur RAG (retrieval +
scoring + visualisations) fonctionne, seules les synthèses rédigées par le LLM
sont remplacées par un résumé déterministe. Pratique pour la démo et robuste en
cas d'indisponibilité de l'API.

## 7. Limites, biais et risques

- **Corpus** : 260 films orientés « classiques » (IMDb), descriptions en anglais →
  biais culturel et de couverture (peu de productions très récentes/nichées).
- **Hallucination** : atténuée (prompts + traçabilité des sources) mais non nulle
  pour les suggestions « hors top 3 » (culture générale du LLM).
- **Dépendance API** : indisponibilité/quotas Gemini → prévoir un mode dégradé.
- **RGPD** : les réponses libres sont stockées localement (`user_responses.json`,
  gitignoré) ; à encadrer (consentement, durée de conservation) en production.

## 8. Pistes d'industrialisation

- Persister les embeddings (FAISS / base vectorielle) au lieu d'un CSV recalculé.
- Conteneuriser (Docker) + CI (tests + éval automatique à chaque commit).
- Monitoring qualité en continu (les métriques d'`evaluation/` comme garde-fou de
  non-régression), supervision des coûts/latence API, A/B testing des paramètres.

## 9. Dépannage

- `streamlit` introuvable → vérifiez que le venv est activé.
- Erreur de clé API → vérifiez que `.env` existe et contient une clé valide.
- Premier lancement lent → SBERT télécharge le modèle (~uniquement la 1ʳᵉ fois).
