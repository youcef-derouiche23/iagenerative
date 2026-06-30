"""
Module de Visualisation
Graphiques et visualisations interactives pour les résultats

Visualisations:
- Graphique radar des préférences par genre
- Graphique radar des moods
- Barres de scores de similarité
- Distribution des genres par affinité
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List
import pandas as pd
import numpy as np


class VisualizationManager:
    """Gestionnaire des visualisations pour l'application"""
    
    def __init__(self):
        """Initialise le gestionnaire de visualisation"""
        self.color_scheme = {
            'primary': '#FF6B6B',
            'secondary': '#4ECDC4',
            'accent': '#FFE66D',
            'dark': '#2C3E50',
            'light': '#ECF0F1'
        }
    
    def plot_genre_radar(
        self,
        genre_weights: Dict[str, float],
        title: str = " Vos Préférences par Genre"
    ):
        """
        Crée un graphique radar des préférences de genre
        
        Args:
            genre_weights: Dictionnaire {genre: poids [0,1]}
            title: Titre du graphique
        """
        genres = list(genre_weights.keys())
        values = list(genre_weights.values())
        
        # Fermer le radar
        genres_closed = genres + [genres[0]]
        values_closed = values + [values[0]]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=genres_closed,
            fill='toself',
            fillcolor='rgba(255, 107, 107, 0.3)',
            line=dict(color='rgb(255, 107, 107)', width=2),
            name='Préférences'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    tickmode='linear',
                    tick0=0,
                    dtick=0.2
                )
            ),
            showlegend=False,
            title=dict(text=title, x=0.5, xanchor='center'),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def plot_mood_radar(
        self,
        mood_weights: Dict[str, float],
        title: str = " Vos Préférences d'Ambiance"
    ):
        """
        Crée un graphique radar des préférences de mood
        
        Args:
            mood_weights: Dictionnaire {mood: poids [0,1]}
            title: Titre du graphique
        """
        moods = list(mood_weights.keys())
        values = list(mood_weights.values())
        
        # Fermer le radar
        moods_closed = moods + [moods[0]]
        values_closed = values + [values[0]]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=moods_closed,
            fill='toself',
            fillcolor='rgba(78, 205, 196, 0.3)',
            line=dict(color='rgb(78, 205, 196)', width=2),
            name='Ambiances'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    tickmode='linear',
                    tick0=0,
                    dtick=0.2
                )
            ),
            showlegend=False,
            title=dict(text=title, x=0.5, xanchor='center'),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def plot_recommendation_scores(
        self,
        recommendations: List[Dict],
        title: str = " Scores des Recommandations"
    ):
        """
        Affiche les scores des films recommandés
        
        Args:
            recommendations: Liste des recommandations
            title: Titre du graphique
        """
        df = pd.DataFrame([
            {
                'Film': f"{r['titre']} ({r['annee']})",
                'Score Final': r['score_final'],
                'Sémantique': r['composantes']['sémantique'],
                'Genre': r['composantes']['genre'],
                'Mood': r['composantes']['mood']
            }
            for r in recommendations[:3]
        ])
        
        # Graphique empilé
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Sémantique (50%)',
            x=df['Film'],
            y=df['Sémantique'] * 0.5,
            marker_color='rgb(255, 107, 107)'
        ))

        fig.add_trace(go.Bar(
            name='Genre (40%)',
            x=df['Film'],
            y=df['Genre'] * 0.4,
            marker_color='rgb(78, 205, 196)'
        ))

        fig.add_trace(go.Bar(
            name='Mood (10%)',
            x=df['Film'],
            y=df['Mood'] * 0.1,
            marker_color='rgb(255, 230, 109)'
        ))
        
        fig.update_layout(
            barmode='stack',
            title=dict(text=title, x=0.5, xanchor='center'),
            yaxis=dict(title='Score Pondéré', range=[0, 1]),
            xaxis=dict(title='Films'),
            height=400,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def plot_genre_distribution(
        self,
        genre_scores: Dict[str, float],
        title: str = " Distribution de l'Affinité par Genre"
    ):
        """
        Affiche la distribution des affinités par genre
        
        Args:
            genre_scores: Dictionnaire {genre: score moyen}
            title: Titre du graphique
        """
        if not genre_scores:
            st.info("Aucune distribution de genre disponible")
            return
        
        df = pd.DataFrame([
            {'Genre': genre, 'Affinité': score}
            for genre, score in sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)
        ])
        
        fig = px.bar(
            df,
            x='Genre',
            y='Affinité',
            color='Affinité',
            color_continuous_scale='RdYlGn',
            title=title
        )
        
        fig.update_layout(
            height=400,
            xaxis_tickangle=-45,
            yaxis=dict(range=[0, 1])
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def display_film_card(self, film: Dict, rank: int):
        """
        Affiche une carte détaillée pour un film
        
        Args:
            film: Dictionnaire du film
            rank: Rang de la recommandation
        """
        # Émojis de médailles
        medals = {1: "1.", 2: "2.", 3: "3."}
        medal = medals.get(rank, "")
        
        with st.container():
            st.markdown(f"### {medal} #{rank} - {film['titre']}")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Réalisateur:** {film['realisateur']}")
                st.markdown(f"**Année:** {film['annee']}")
                st.markdown(f"**Genre:** {film['genre']}")
                st.markdown(f"**Ambiance:** {film['mood']}")
                
                st.markdown("**Synopsis:**")
                st.write(film['description'])
                
                st.markdown(f"**Mots-clés:** `{film['keywords']}`")
            
            with col2:
                # Scores
                st.metric("Score Final", f"{film['score_final']:.2%}")
                
                st.markdown("**Composantes:**")
                st.progress(film['composantes']['sémantique'], text=f"Sémantique: {film['composantes']['sémantique']:.2%}")
                st.progress(film['composantes']['genre'], text=f"Genre: {film['composantes']['genre']:.2%}")
                st.progress(film['composantes']['mood'], text=f"Mood: {film['composantes']['mood']:.2%}")
            
            st.markdown("---")
    
    def display_coverage_stats(self, stats: Dict):
        """
        Affiche les statistiques de couverture
        
        Args:
            stats: Dictionnaire des statistiques
        """
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Score Moyen",
                f"{stats['score_moyen']:.2%}",
                help="Affinité moyenne avec l'ensemble du catalogue"
            )
        
        with col2:
            st.metric(
                "Haute Affinité",
                stats['films_haute_affinite'],
                help="Films avec score > 70%"
            )
        
        with col3:
            st.metric(
                "Affinité Moyenne",
                stats['films_affinite_moyenne'],
                help="Films avec score 50-70%"
            )
        
        with col4:
            st.metric(
                "À Découvrir",
                stats['films_faible_affinite'],
                help="Films avec score < 50% (nouveaux horizons)"
            )
    
    def display_api_usage(self, api_stats: Dict):
        """
        Affiche les statistiques d'utilisation de l'API GenAI
        
        Args:
            api_stats: Statistiques de l'API
        """
        st.markdown("###  Utilisation de l'API GenAI")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Appels API",
                api_stats['api_calls_count'],
                help="Nombre d'appels effectués à Gemini"
            )
        
        with col2:
            cache_stats = api_stats['cache_stats']
            st.metric(
                "Entrées en Cache",
                f"{cache_stats['entries']}/{cache_stats['max_size']}",
                help="Réponses mises en cache pour réutilisation"
            )
        
        with col3:
            st.metric(
                "Taux d'Utilisation Cache",
                f"{cache_stats['usage_percent']:.1f}%",
                help="Pourcentage du cache utilisé"
            )
