"""
Moteur NLP avec SBERT pour l'analyse semantique des preferences
"""

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class NLPEngine:
    """Moteur d'analyse semantique SBERT"""
    
    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        """Initialise le modele SBERT"""
        logger.info(f"Chargement du modèle SBERT: {model_name}")
        
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.referentiel = None
        self.embeddings_cache = {}
        # Cache des embeddings du référentiel : calculé une seule fois puis
        # réutilisé à chaque requête (avant : ré-encodage complet à chaque
        # analyse → latence/coût inutiles, non scalable). Cf. correctif audit.
        self.referentiel_embeddings = None
        
        logger.info("Modèle SBERT chargé avec succès")
    
    def load_referentiel(self, filepath: str = 'data/films_referentiel.csv') -> pd.DataFrame:
        """Charge la base de films depuis le CSV"""
        logger.info(f"Chargement du référentiel: {filepath}")
        
        self.referentiel = pd.read_csv(filepath)
        self.referentiel_embeddings = None  # invalide le cache au rechargement
        self.referentiel['texte_complet'] = self.referentiel.apply(
            lambda row: self._build_film_text(row),
            axis=1
        )
        
        logger.info(f"Referentiel chargé: {len(self.referentiel)} films")
        return self.referentiel
    
    def _build_film_text(self, row: pd.Series) -> str:
        """Construit le texte complet pour l'embedding"""
        return (
            f"{row['Film']} ({row['Annee']}). "
            f"Réalisé par {row['Realisateur']}. "
            f"Genre: {row['Genre']}. "
            f"Description: {row['Description']} "
            f"Mots-clés: {row['Keywords']}. "
            f"Ambiance: {row['Mood']}."
        )
    
    def encode_text(self, text: str, cache_key: Optional[str] = None) -> np.ndarray:
        """Encode un texte en vecteur d'embeddings"""
        if cache_key and cache_key in self.embeddings_cache:
            logger.debug(f"Cache HIT pour: {cache_key}")
            return self.embeddings_cache[cache_key]
        
        embedding = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        
        if cache_key:
            self.embeddings_cache[cache_key] = embedding
            logger.debug(f"Embedding mis en cache: {cache_key}")
        
        return embedding
    
    def encode_referentiel(self, force: bool = False) -> np.ndarray:
        """Encode tous les films du référentiel (mémorisé après le 1er appel).

        Args:
            force: recalcule les embeddings même s'ils sont déjà en cache.
        """
        if self.referentiel is None:
            raise ValueError("Le référentiel doit être chargé avant l'encodage")

        if self.referentiel_embeddings is not None and not force:
            logger.debug("Embeddings du référentiel servis depuis le cache mémoire")
            return self.referentiel_embeddings

        logger.info(f"Encodage de {len(self.referentiel)} films...")

        embeddings = self.model.encode(
            self.referentiel['texte_complet'].tolist(),
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=32
        )

        self.referentiel_embeddings = embeddings
        logger.info(f"Encodage terminé - Shape: {embeddings.shape}")
        return embeddings
    
    def calculate_similarity(
        self, 
        user_embedding: np.ndarray, 
        referentiel_embeddings: np.ndarray
    ) -> np.ndarray:
        """Calcule la similarité cosinus"""
        if user_embedding.ndim == 1:
            user_embedding = user_embedding.reshape(1, -1)
        
        similarities = cosine_similarity(user_embedding, referentiel_embeddings)[0]
        
        logger.info(f"Similarité - Min: {similarities.min():.3f}, "
                   f"Max: {similarities.max():.3f}, Moyenne: {similarities.mean():.3f}")
        
        return similarities
    
    def get_top_matches(
        self, 
        similarities: np.ndarray, 
        top_n: int = 3
    ) -> List[Tuple[int, float]]:
        """Recupere les top N films les plus similaires"""
        top_indices = np.argsort(similarities)[::-1][:top_n]
        results = [(idx, float(similarities[idx])) for idx in top_indices]
        
        logger.info(f"Top {top_n} matches: {[f'{s:.3f}' for _, s in results]}")
        return results
    
    def analyze_user_input(
        self, 
        user_text: str, 
        top_n: int = 3
    ) -> Tuple[List[Dict], np.ndarray]:
        """Pipeline d'analyse semantique complet"""
        if self.referentiel is None:
            raise ValueError("Le référentiel doit être chargé avant l'analyse")
        
        logger.info("Début de l'analyse sémantique...")
        
        user_embedding = self.encode_text(user_text, cache_key="current_user_query")
        referentiel_embeddings = self.encode_referentiel()
        similarities = self.calculate_similarity(user_embedding, referentiel_embeddings)
        top_matches = self.get_top_matches(similarities, top_n)
        
        recommendations = []
        for idx, score in top_matches:
            film = self.referentiel.iloc[idx]
            recommendations.append({
                'film_id': film['FilmID'],
                'titre': film['Film'],
                'realisateur': film['Realisateur'],
                'annee': int(film['Annee']),
                'genre': film['Genre'],
                'categorie': film['Categorie'],
                'description': film['Description'],
                'keywords': film['Keywords'],
                'mood': film['Mood'],
                'block_id': film['BlockID'],
                'score_similarite': float(score),
                'rang': len(recommendations) + 1
            })
        
        logger.info(f"Analyse terminée: {len(recommendations)} recommandations")
        return recommendations, similarities
    
    def get_genre_distribution(
        self, 
        similarities: np.ndarray, 
        threshold: float = 0.5
    ) -> Dict[str, float]:
        """Analyse la distribution des genres par similarite"""
        if self.referentiel is None:
            return {}
        
        mask = similarities >= threshold
        
        if not mask.any():
            logger.warning(f"Aucun film au-dessus du seuil {threshold}")
            return {}
        
        genre_scores = {}
        for genre in self.referentiel['Categorie'].unique():
            genre_mask = self.referentiel['Categorie'] == genre
            combined_mask = mask & genre_mask
            
            if combined_mask.any():
                genre_scores[genre] = float(similarities[combined_mask].mean())
        
        sorted_genres = dict(sorted(genre_scores.items(), key=lambda x: x[1], reverse=True))
        logger.info(f"Distribution: {len(sorted_genres)} genres")
        
        return sorted_genres
    
    def get_coverage_stats(self, similarities: np.ndarray) -> Dict:
        """Statistiques de couverture du profil utilisateur"""
        return {
            'score_moyen': float(similarities.mean()),
            'score_median': float(np.median(similarities)),
            'score_max': float(similarities.max()),
            'score_min': float(similarities.min()),
            'films_haute_affinite': int((similarities >= 0.7).sum()),
            'films_affinite_moyenne': int(((similarities >= 0.5) & (similarities < 0.7)).sum()),
            'films_faible_affinite': int((similarities < 0.5).sum()),
            'total_films': len(similarities)
        }
