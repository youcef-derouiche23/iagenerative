"""
Module pour utiliser l'IA Gemini de Google
Genere du texte personnalise pour l'utilisateur

Contraintes respectees:
- Maximum 2-3 appels API par session
- Utilise un cache pour eviter les appels repetitifs
- Enrichit le texte utilisateur seulement si necessaire
"""

import os
from typing import List, Dict, Optional
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from src.cache_manager import CacheManager

load_dotenv()

logger = logging.getLogger(__name__)


def _get_api_key() -> Optional[str]:
    """Récupère la clé API depuis st.secrets (Cloud) ou .env (local)"""
    try:
        import streamlit as st
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY")


def _get_model_name() -> str:
    """Récupère le nom du modèle depuis st.secrets (Cloud) ou .env (local)"""
    try:
        import streamlit as st
        return st.secrets.get("GEMINI_MODEL", "gemini-2.0-flash")
    except Exception:
        return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def _get_generation_config() -> Dict:
    """Construit la configuration de génération depuis l'environnement.

    Exposer ces paramètres (température, top_p, top_k, max_output_tokens) est
    indispensable pour C5.3 : ils permettent d'illustrer et de mesurer l'effet
    d'un ajustement (cf. evaluation/compare_params.py). Sans eux, l'appel
    `generate_content` utilisait des valeurs par défaut opaques et non ajustables.
    """
    def _f(name, default):
        try:
            return float(os.getenv(name, default))
        except (TypeError, ValueError):
            return float(default)

    def _i(name, default):
        try:
            return int(os.getenv(name, default))
        except (TypeError, ValueError):
            return int(default)

    return {
        "temperature": _f("GEMINI_TEMPERATURE", 0.7),
        "top_p": _f("GEMINI_TOP_P", 0.95),
        "top_k": _i("GEMINI_TOP_K", 40),
        "max_output_tokens": _i("GEMINI_MAX_OUTPUT_TOKENS", 1024),
    }


class GenAIIntegration:
    """
    Classe pour integrer l'IA Gemini dans l'application
    Gere les appels API et le cache pour limiter les couts
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = None,
        cache_enabled: bool = True,
        max_cache_size: int = 100,
        generation_config: Optional[Dict] = None
    ):
        self.api_key = api_key or _get_api_key()
        self.model_name = model_name or _get_model_name()
        # Paramètres de génération ajustables (C5.3). Surchargeable par appelant
        # (utilisé par le script de comparaison de paramètres avant/après).
        self.generation_config = generation_config or _get_generation_config()

        if not self.api_key:
            raise ValueError(
                "Cle API Gemini manquante. "
                "Ajoutez GEMINI_API_KEY dans Streamlit Secrets ou le fichier .env"
            )

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            self.model_name,
            generation_config=genai.types.GenerationConfig(**self.generation_config)
        )

        # Utilise /tmp pour le cache (accessible sur Streamlit Cloud)
        self.cache = CacheManager(
            cache_dir="/tmp/.cache",
            max_size=max_cache_size,
            enabled=cache_enabled
        )

        self.api_calls_count = 0

        logger.info(
            f"GenAI initialisé - Modèle: {self.model_name}, Cache: {cache_enabled}, "
            f"Config: {self.generation_config}"
        )

    def _call_gemini(self, prompt: str, use_cache: bool = True) -> str:
        """Appelle l'API Gemini avec gestion du cache.

        La clé de cache intègre les paramètres de génération : deux réglages
        différents (ex. température 0.2 vs 0.9) ne doivent pas partager la même
        réponse cachée, sinon la comparaison avant/après serait faussée.
        """
        cache_model = f"{self.model_name}|{sorted(self.generation_config.items())}"
        if use_cache:
            cached_response = self.cache.get(prompt, model=cache_model)
            if cached_response:
                logger.info("Réponse trouvée dans le cache")
                return cached_response

        try:
            logger.info(f"Appel API Gemini #{self.api_calls_count + 1}")
            response = self.model.generate_content(prompt)
            result = response.text

            if use_cache:
                self.cache.set(prompt, result, model=cache_model)

            self.api_calls_count += 1
            logger.info(f"Réponse générée ({len(result)} caractères)")
            return result

        except Exception as e:
            logger.error(f"Erreur appel API Gemini: {e}")
            return f"[Erreur de génération: {str(e)}]"

    # Garde-fou anti-hallucination commun à tous les prompts (C5.2/C5.3) :
    # le LLM ne doit pas inventer de faits sur les films recommandés.
    _ANTI_HALLUCINATION = (
        "\n\nRÈGLES DE FIABILITÉ (impératif) :\n"
        "- Ne fabrique AUCUN fait (date, casting, récompense) sur les films listés ; "
        "appuie-toi uniquement sur les données fournies ci-dessus.\n"
        "- Si une information manque, reste général plutôt que d'inventer.\n"
        "- Toute suggestion de film hors de la liste relève de la culture générale "
        "et doit être présentée comme une piste, non comme une certitude."
    )

    def enrich_short_text(self, text: str, min_words: int = 15) -> tuple[str, bool]:
        """Enrichit conditionnellement un texte trop court"""
        word_count = len(text.split())

        if word_count >= min_words:
            logger.info(f"Texte suffisant ({word_count} mots) - Pas d'enrichissement")
            return text, False

        logger.info(f"Texte court ({word_count} mots) - Enrichissement via GenAI")

        prompt = f"""Tu es un assistant qui enrichit des descriptions de préférences cinématographiques.

Description courte de l'utilisateur : "{text}"

Tâche : Enrichis cette description en ajoutant du contexte technique et des détails sur :
- Les thèmes cinématographiques possibles
- L'atmosphère recherchée
- Le style narratif qui pourrait correspondre

Règles :
- Reste fidèle à l'intention originale
- Ajoute 2-3 phrases maximum
- Utilise un ton naturel
- Ne change pas les préférences exprimées, ajoute seulement du contexte

Description enrichie :"""

        enriched = self._call_gemini(prompt, use_cache=True)
        final_text = f"{text}\n\n{enriched.strip()}"
        logger.info(f"Texte enrichi ({len(final_text.split())} mots)")
        return final_text, True

    def generate_discovery_plan(
        self,
        weak_genres: List[str],
        recommendations: List[Dict],
        user_profile_summary: str
    ) -> str:
        """Génère le Plan de Découverte (1 appel API)"""
        logger.info("Génération du plan de découverte")

        reco_text = "\n".join([
            f"- {r['titre']} ({r['annee']}) de {r['realisateur']} - Score: {r['score_final']:.2f}"
            for r in recommendations[:3]
        ])

        weak_genres_text = ", ".join(weak_genres[:5]) if weak_genres else "Aucun"

        prompt = f"""Tu es un conseiller cinématographique expert qui crée des plans de découverte personnalisés.

PROFIL UTILISATEUR :
{user_profile_summary}

FILMS RECOMMANDÉS (Top 3) :
{reco_text}

GENRES À EXPLORER (faible affinité actuelle) :
{weak_genres_text}

TÂCHE : Crée un plan de découverte cinématographique personnalisé incluant :

1. **Prochaines Étapes** : 3-4 films à découvrir en priorité (en dehors du top 3) pour enrichir le profil
2. **Genres à Explorer** : Pourquoi découvrir les genres faiblement couverts et films recommandés par genre
3. **Parcours Thématique** : Une progression logique (ex: du plus accessible au plus expérimental)

Ton : Enthousiaste, pédagogique, personnalisé
Format : Markdown avec sections claires
Longueur : 300-400 mots maximum
{self._ANTI_HALLUCINATION}

Plan de Découverte :"""

        plan = self._call_gemini(prompt, use_cache=True)
        logger.info("Plan de découverte généré")
        return plan.strip()

    def generate_cinephile_profile(
        self,
        recommendations: List[Dict],
        genre_weights: Dict[str, float],
        mood_weights: Dict[str, float],
        coverage_score: float
    ) -> str:
        """Génère le Profil Cinéphile (1 appel API)"""
        logger.info("Génération du profil cinéphile")

        top_genres = [g for g, w in sorted(genre_weights.items(), key=lambda x: x[1], reverse=True) if w > 0.7][:3]
        top_moods = [m for m, w in sorted(mood_weights.items(), key=lambda x: x[1], reverse=True) if w > 0.7][:3]
        reco_titles = [f"{r['titre']} ({r['annee']})" for r in recommendations[:3]]

        prompt = f"""Tu es un expert en profils cinématographiques qui rédige des synthèses personnalisées.

DONNÉES DU PROFIL :
- Genres préférés : {', '.join(top_genres) if top_genres else 'Varié'}
- Ambiances recherchées : {', '.join(top_moods) if top_moods else 'Varié'}
- Films recommandés : {', '.join(reco_titles)}
- Score d'affinité global : {coverage_score:.2f}/1.00

TÂCHE : Rédige un profil cinéphile personnalisé (style executive summary) qui :

1. Résume les goûts cinématographiques de la personne
2. Identifie sa "signature" de cinéphile (qu'est-ce qui caractérise ses choix ?)
3. Mentionne les réalisateurs ou mouvements qui pourraient l'intéresser
4. Termine par une phrase accrocheuse qui capture son essence de spectateur

Ton : Professionnel mais chaleureux, précis, valorisant
Format : Un seul paragraphe fluide
Longueur : 150-200 mots maximum
{self._ANTI_HALLUCINATION}

Profil Cinéphile :"""

        profile = self._call_gemini(prompt, use_cache=True)
        logger.info("Profil cinéphile généré")
        return profile.strip()

    def generate_film_justification(
        self,
        film: Dict,
        user_description: str,
        score_components: Dict[str, float]
    ) -> str:
        """Génère une justification pour une recommandation"""
        prompt = f"""Explique en 2-3 phrases pourquoi le film "{film['titre']}" ({film['annee']}) 
correspond aux préférences de l'utilisateur.

Préférences utilisateur : {user_description[:200]}...

Description du film : {film['description'][:300]}...

Scores :
- Similarité sémantique : {score_components['sémantique']:.2f}
- Affinité genre : {score_components['genre']:.2f}
- Affinité mood : {score_components['mood']:.2f}

Justification concise et personnalisée :"""

        return self._call_gemini(prompt, use_cache=True).strip()

    def get_api_stats(self) -> Dict:
        """Retourne les statistiques d'utilisation"""
        return {
            "api_calls_count": self.api_calls_count,
            "cache_stats": self.cache.get_stats(),
            "model_name": self.model_name,
            "generation_config": self.generation_config
        }
