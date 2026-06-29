"""
Application de recommandation de films avec IA
"""

import streamlit as st
import logging
from pathlib import Path

from src.questionnaire import QuestionnaireManager
from src.nlp_engine import NLPEngine
from src.scoring import ScoringSystem
from src.genai_integration import GenAIIntegration
from src.visualization import VisualizationManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AISCA-Cinema | Recommandation Cinématographique IA",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
    
    .stApp {
        background: linear-gradient(180deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    .main .block-container {
        background: linear-gradient(180deg, #1a1a2e 0%, #0f3460 100%);
        border-radius: 20px;
        padding: 2.5rem;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(14, 165, 233, 0.2);
    }
    
    /* Header principal avec gradient cyan-bleu */
    .main-header {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        padding: 1rem 0;
        filter: drop-shadow(0 0 20px rgba(14, 165, 233, 0.3));
    }
    
    /* Sous-titre elegant */
    .sub-header {
        text-align: center;
        color: #94a3b8;
        font-size: 1.2rem;
        margin-bottom: 3rem;
        font-weight: 300;
    }
    
    /* Boutons modernes avec gradient cyan */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-size: 1.1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(14, 165, 233, 0.6);
        background: linear-gradient(135deg, #06b6d4 0%, #0ea5e9 100%);
    }
    
    /* Tabs modernes sombres */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(15, 23, 42, 0.8);
        padding: 0.5rem;
        border-radius: 12px;
        border: 1px solid rgba(14, 165, 233, 0.2);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        color: #94a3b8;
        background: transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);
        color: white !important;
    }
    
    /* Cards et containers sombres */
    .stExpander {
        border: 1px solid rgba(14, 165, 233, 0.3);
        border-radius: 12px;
        background: rgba(15, 23, 42, 0.6);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    /* Metriques modernes avec couleur cyan */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Messages info avec theme sombre */
    .stInfo {
        background: rgba(14, 165, 233, 0.1);
        border-left: 4px solid #0ea5e9;
        border-radius: 12px;
        color: #e0f2fe;
    }
    
    .stSuccess {
        background: rgba(34, 197, 94, 0.1);
        border-left: 4px solid #22c55e;
        border-radius: 12px;
        color: #dcfce7;
    }
    
    .stWarning {
        background: rgba(245, 158, 11, 0.1);
        border-left: 4px solid #f59e0b;
        border-radius: 12px;
        color: #fef3c7;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1);
        border-left: 4px solid #ef4444;
        border-radius: 12px;
        color: #fee2e2;
    }
    
    /* Espacement global */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* Inputs et selects theme sombre */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(14, 165, 233, 0.3);
        border-radius: 8px;
        color: #e2e8f0;
        transition: all 0.3s ease;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
        border-color: #0ea5e9;
        box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.2);
        background: rgba(15, 23, 42, 0.9);
    }
    
    /* Labels en clair pour contraste */
    label {
        color: #cbd5e1 !important;
    }
    
    /* Texte general */
    .stMarkdown, p, span {
        color: #cbd5e1;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #e2e8f0;
    }
    
    /* Separateurs */
    hr {
        border-color: rgba(14, 165, 233, 0.2);
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialise les variables de session"""
    if 'responses' not in st.session_state:
        st.session_state.responses = None
    if 'recommendations' not in st.session_state:
        st.session_state.recommendations = None
    if 'analysis_done' not in st.session_state:
        st.session_state.analysis_done = False


def main():
    """Fonction principale de l'application"""
    
    initialize_session_state()
    
    # Header principal avec badge de projet
    st.markdown('<h1 class="main-header">AISCA-Cinema</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Agent Intelligent de Recommandation Cinématographique propulsé par IA</p>',
        unsafe_allow_html=True
    )
    
    # Badge du projet en haut
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("**Projet EFREI 2025-26** | Module IA Générative | RNCP40875 - Bloc 2")
    
    st.markdown("---")
    
    # Etape 1 - Affichage du questionnaire
    if not st.session_state.analysis_done:
        st.markdown("## Questionnaire de Préférences")
        st.markdown("Répondez aux questions ci-dessous pour obtenir vos recommandations personnalisées.")
        
        questionnaire = QuestionnaireManager()
        responses = questionnaire.render_questionnaire()
        
        st.markdown("---")
        
        # Bouton d'analyse centre
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            analyze_button = st.button("Analyser mes Préférences", type="primary", use_container_width=True)
        
        # Bouton de reinitialisation si deja analyse
        if st.session_state.get('recommendations'):
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("Nouvelle Analyse", use_container_width=True):
                    st.session_state.responses = None
                    st.session_state.recommendations = None
                    st.session_state.analysis_done = False
                    st.rerun()
        
        if analyze_button:
            # Valider les réponses
            is_valid, message = questionnaire.validate_responses(responses)
            
            if not is_valid:
                st.error(message)
            else:
                st.success(message)
                
                # Sauvegarder les reponses de l'utilisateur
                questionnaire.save_responses(responses)
                
                # Stocker les reponses dans la session
                st.session_state.responses = responses
                
                # Lancer le processus d'analyse
                with st.spinner("Analyse en cours... Veuillez patienter."):
                    try:
                        # Etape 1 - Initialiser les composants necessaires
                        st.toast("Initialisation des composants...")
                        nlp_engine = NLPEngine()
                        scoring_system = ScoringSystem(alpha=0.50, beta=0.30, gamma=0.20)
                        # Mode degrade : si la cle API est absente, le coeur RAG
                        # (retrieval + scoring) reste fonctionnel ; seules les
                        # syntheses redigees par le LLM sont remplacees par un
                        # resume deterministe. Resilience + demo sans cle.
                        try:
                            genai = GenAIIntegration()
                            genai_available = True
                        except Exception as genai_err:
                            genai = None
                            genai_available = False
                            logger.warning(f"GenAI indisponible (mode degrade): {genai_err}")
                            st.warning("IA générative indisponible (clé API manquante) : "
                                       "affichage des recommandations sans les synthèses rédigées.")
                        
                        # Etape 2 - Charger la base de donnees de films
                        st.toast("Chargement du référentiel de films...")
                        csv_path = Path(__file__).parent / 'data' / 'films_referentiel.csv'
                        referentiel = nlp_engine.load_referentiel(str(csv_path))
                        
                        # Etape 3 - Preparer le texte utilisateur pour l'analyse
                        user_text = questionnaire.get_text_for_analysis(responses)
                        
                        # Etape 4 - Enrichir le texte si trop court avec l'IA
                        if genai_available:
                            user_text, was_enriched = genai.enrich_short_text(user_text, min_words=15)
                            if was_enriched:
                                st.toast("Description enrichie par l'IA")
                        
                        # Etape 5 - Analyse semantique avec SBERT
                        st.toast("Analyse sémantique avec SBERT...")
                        recommendations, similarities = nlp_engine.analyze_user_input(user_text, top_n=3)
                        
                        # Etape 6 - Calculer les scores ponderes
                        st.toast("Calcul des scores finaux...")
                        genre_weights = questionnaire.get_genre_weights(responses)
                        mood_weights = questionnaire.get_mood_weights(responses)
                        
                        ranked_recommendations = scoring_system.rank_films(
                            recommendations=recommendations,
                            semantic_similarities=similarities,
                            user_genre_weights=genre_weights,
                            user_mood_weights=mood_weights,
                            referentiel=referentiel
                        )
                        
                        # Etape 7 - Recuperer le top 3 des films
                        top_3 = scoring_system.get_top_recommendations(ranked_recommendations, top_n=3)
                        
                        # Etape 8 - Calculer les statistiques
                        coverage_stats = nlp_engine.get_coverage_stats(similarities)
                        genre_distribution = nlp_engine.get_genre_distribution(similarities, threshold=0.5)
                        coverage_score = scoring_system.calculate_coverage_score(
                            similarities, genre_weights, mood_weights, referentiel
                        )
                        weak_genres = scoring_system.identify_weak_genres(similarities, referentiel, threshold=0.4)
                        
                        # Etape 9 - Generation avec l'IA Gemini
                        st.toast("Génération du profil et du plan...")
                        
                        # Generer le plan de decouverte + profil (1 appel API chacun)
                        top_genres_txt = ', '.join([g for g, w in sorted(genre_weights.items(), key=lambda x: x[1], reverse=True)[:3]])
                        top_moods_txt = ', '.join([m for m, w in sorted(mood_weights.items(), key=lambda x: x[1], reverse=True)[:3]])
                        if genai_available:
                            user_profile_summary = f"Genres préférés: {top_genres_txt}. Moods: {top_moods_txt}."
                            discovery_plan = genai.generate_discovery_plan(weak_genres, top_3, user_profile_summary)
                            cinephile_profile = genai.generate_cinephile_profile(
                                top_3, genre_weights, mood_weights, coverage_score
                            )
                        else:
                            # Resume deterministe (sans LLM) pour le mode degrade
                            films_txt = ", ".join(f"{f['titre']} ({f['annee']})" for f in top_3)
                            cinephile_profile = (
                                f"*(Synthèse automatique — IA générative non disponible)*\n\n"
                                f"Vos genres de prédilection sont **{top_genres_txt}**, avec une "
                                f"recherche d'ambiance **{top_moods_txt}**. Les films les plus "
                                f"proches de votre profil sont : {films_txt}. "
                                f"Score d'affinité global : {coverage_score:.0%}."
                            )
                            weak_txt = ", ".join(weak_genres[:5]) if weak_genres else "aucun en particulier"
                            discovery_plan = (
                                f"*(Plan automatique — IA générative non disponible)*\n\n"
                                f"À partir de {films_txt}, élargissez vers les genres encore peu "
                                f"explorés : **{weak_txt}**. Renseignez une clé API Gemini dans "
                                f"`.env` pour obtenir un plan rédigé et personnalisé."
                            )
                        
                        # Sauvegarder tous les resultats
                        st.session_state.recommendations = {
                            'top_3': top_3,
                            'all_recommendations': ranked_recommendations,
                            'similarities': similarities,
                            'coverage_stats': coverage_stats,
                            'genre_distribution': genre_distribution,
                            'coverage_score': coverage_score,
                            'weak_genres': weak_genres,
                            'discovery_plan': discovery_plan,
                            'cinephile_profile': cinephile_profile,
                            'genre_weights': genre_weights,
                            'mood_weights': mood_weights,
                            'api_stats': genai.get_api_stats() if genai_available else {
                                'api_calls_count': 0,
                                'cache_stats': {'entries': 0, 'max_size': 0, 'usage_percent': 0},
                                'model_name': 'indisponible (mode dégradé)'
                            }
                        }
                        
                        st.session_state.analysis_done = True
                        st.success("Analyse terminée !")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Erreur lors de l'analyse: {str(e)}")
                        logger.error(f"Erreur analyse: {e}", exc_info=True)
    
    # Etape 2 - Affichage des resultats
    else:
        viz = VisualizationManager()
        results = st.session_state.recommendations
        responses = st.session_state.responses
        
        # Bouton nouvelle analyse en haut
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("Nouvelle Analyse", use_container_width=True):
                st.session_state.responses = None
                st.session_state.recommendations = None
                st.session_state.analysis_done = False
                st.rerun()
        
        st.markdown("---")
        st.markdown("## Vos Recommandations Personnalisées")
        st.markdown("---")
        
        # Organiser les resultats en onglets
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Top 3 Films",
            "Visualisations",
            "Profil Cinéphile",
            "Plan de Découverte",
            "Statistiques"
        ])
        
        # Onglet 1 - Les 3 meilleurs films recommandes
        with tab1:
            st.markdown("### Vos 3 Films Recommandés")
            
            for film in results['top_3']:
                viz.display_film_card(film, film['rang'])
        
        # Onglet 2 - Graphiques et visualisations
        with tab2:
            st.markdown("### Analyse Visuelle de votre Profil")
            
            col1, col2 = st.columns(2)
            
            with col1:
                viz.plot_genre_radar(results['genre_weights'])
            
            with col2:
                viz.plot_mood_radar(results['mood_weights'])
            
            viz.plot_recommendation_scores(results['top_3'])
            
            viz.plot_genre_distribution(results['genre_distribution'])
            
            st.markdown("### Statistiques de Couverture")
            viz.display_coverage_stats(results['coverage_stats'])
        
        # Onglet 3 - Profil personnalise genere par l'IA
        with tab3:
            st.markdown("### Votre Profil Cinéphile")
            st.info("Généré par l'IA Gemini (1 appel API - EF4.3)")
            
            st.markdown(results['cinephile_profile'])

            # Traçabilité RAG : films réellement utilisés comme contexte (sources)
            with st.expander("Sources (films ayant servi de contexte à la génération)"):
                st.caption("Le profil est généré à partir de ces films récupérés "
                           "par l'analyse sémantique — pas d'invention hors corpus.")
                for f in results['top_3']:
                    st.markdown(f"- **{f['titre']}** ({f['annee']}) — {f['genre']} "
                                f"· score {f['score_final']:.0%}")

            st.markdown("---")
            st.markdown(f"**Score d'Affinité Global:** {results['coverage_score']:.1%}")
            
            # Interpreter le score pour l'utilisateur
            if results['coverage_score'] >= 0.7:
                st.success("Excellent ! Vos goûts sont très bien définis.")
            elif results['coverage_score'] >= 0.5:
                st.info("Bon profil cinématographique avec de la diversité.")
            else:
                st.warning("Profil varié ! Vous êtes ouvert à de nombreux styles.")
        
        # Onglet 4 - Plan de decouverte personnalise
        with tab4:
            st.markdown("### Plan de Découverte Personnalisé")
            st.info("Généré par l'IA Gemini (1 appel API - EF4.2)")
            
            st.markdown(results['discovery_plan'])

            # Traçabilité RAG des sources du plan
            with st.expander("Sources (films de référence du plan)"):
                st.caption("Plan ancré sur les films récupérés par AISCA. Les films "
                           "hors top 3 cités relèvent de pistes de culture générale.")
                for f in results['top_3']:
                    st.markdown(f"- **{f['titre']}** ({f['annee']}) — {f['genre']}")

            if results['weak_genres']:
                st.markdown("### Genres à Explorer")
                cols = st.columns(len(results['weak_genres'][:5]))
                for idx, genre in enumerate(results['weak_genres'][:5]):
                    with cols[idx]:
                        st.metric(f"Genre #{idx+1}", genre)
        
        # Onglet 5 - Details techniques et statistiques
        with tab5:
            st.markdown("### Détails Techniques de l'Analyse")
            
            st.markdown("#### Analyse Sémantique (SBERT)")
            st.json({
                "Modèle": "paraphrase-multilingual-MiniLM-L12-v2",
                "Type": "Sentence-BERT (Embeddings Contextuels)",
                "Mesure": "Similarité Cosinus",
                "Films analysés": results['coverage_stats']['total_films']
            })
            
            st.markdown("#### Système de Scoring")
            st.code("""
Formule de Score Final:
Score = 0.50 × Similarité_Sémantique 
      + 0.30 × Score_Genre
      + 0.20 × Score_Mood

Où tous les scores sont normalisés dans [0, 1]
            """)
            
            st.markdown("#### Utilisation de l'IA Générative")
            viz.display_api_usage(results['api_stats'])
            
            st.markdown("#### Données Brutes")
            with st.expander("Voir les scores détaillés"):
                import pandas as pd
                df_scores = pd.DataFrame([
                    {
                        'Rang': r['rang'],
                        'Film': r['titre'],
                        'Score Final': f"{r['score_final']:.3f}",
                        'Sémantique': f"{r['composantes']['sémantique']:.3f}",
                        'Genre': f"{r['composantes']['genre']:.3f}",
                        'Mood': f"{r['composantes']['mood']:.3f}"
                    }
                    for r in results['top_3']
                ])
                st.dataframe(df_scores, use_container_width=True)
    
    # Footer moderne et epure
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #64748b; padding: 2rem 0;'>
            <p style='font-size: 0.9rem; margin-bottom: 0.5rem;'>
                <strong style='background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>AISCA-Cinema</strong> | Recommandation Cinématographique Intelligente
            </p>
            <p style='font-size: 0.85rem; color: #475569;'>
                Projet EFREI 2025-26 • Architecture RAG • SBERT + Gemini AI
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
