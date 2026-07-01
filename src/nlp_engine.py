"""
Moteur NLP avec SBERT pour l'analyse semantique des preferences
"""

import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

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
        # Cache mémoire des embeddings du référentiel : calculé une seule fois
        # puis réutilisé. Persistance disque en plus (cf. encode_referentiel).
        self.referentiel_embeddings = None
        self._faiss_index = None
        # Répertoire de persistance des embeddings (gitignoré)
        self.cache_dir = Path(".cache/embeddings")

        logger.info("Modèle SBERT chargé avec succès")
    
    def load_referentiel(self, filepath: str = 'data/films_referentiel.csv') -> pd.DataFrame:
        """Charge la base de films depuis le CSV"""
        logger.info(f"Chargement du référentiel: {filepath}")
        
        self.referentiel = pd.read_csv(filepath)
        self.referentiel_embeddings = None  # invalide le cache au rechargement
        self._faiss_index = None
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
    
    def _corpus_signature(self) -> str:
        """Empreinte (modèle + contenu du corpus) pour invalider le cache disque."""
        joined = "||".join(self.referentiel['texte_complet'].tolist())
        h = hashlib.sha256((self.model_name + joined).encode("utf-8")).hexdigest()[:16]
        return h

    def encode_referentiel(self, force: bool = False, persist: bool = True) -> np.ndarray:
        """Encode tous les films du référentiel, avec cache mémoire ET disque.

        Avant : ré-encodage complet à chaque requête (latence/coût inutiles).
        Maintenant : calculé une fois, mémorisé en RAM, et persisté sur disque
        (.npy) — au redémarrage on recharge sans réencoder. Scalable (cf.
        industrialisation : remplaçable par un index vectoriel persistant).

        Args:
            force: recalcule même si un cache existe.
            persist: sauvegarde/charge depuis le disque.
        """
        if self.referentiel is None:
            raise ValueError("Le référentiel doit être chargé avant l'encodage")

        if self.referentiel_embeddings is not None and not force:
            logger.debug("Embeddings du référentiel servis depuis le cache mémoire")
            return self.referentiel_embeddings

        cache_file = self.cache_dir / f"ref_{self._corpus_signature()}.npy"
        if persist and not force and cache_file.exists():
            self.referentiel_embeddings = np.load(cache_file)
            logger.info(f"Embeddings rechargés depuis le disque: {cache_file}")
            return self.referentiel_embeddings

        logger.info(f"Encodage de {len(self.referentiel)} films...")
        embeddings = self.model.encode(
            self.referentiel['texte_complet'].tolist(),
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=32,
        )
        self.referentiel_embeddings = embeddings

        if persist:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                np.save(cache_file, embeddings)
                logger.info(f"Embeddings persistés sur disque: {cache_file}")
            except Exception as e:  # pragma: no cover
                logger.warning(f"Persistance embeddings impossible: {e}")

        logger.info(f"Encodage terminé - Shape: {embeddings.shape}")
        return embeddings

    def build_faiss_index(self):
        """Construit un index FAISS (cosine via produit scalaire normalisé).

        Optionnel : accélère et rend scalable la recherche de similarité pour de
        grands corpus (industrialisation). Sans FAISS installé, on retombe sur le
        calcul cosinus dense (sklearn) — voir faiss_search.
        """
        try:
            import faiss
        except Exception as e:
            logger.warning(f"FAISS indisponible ({e}) — repli sur cosinus dense.")
            return None
        emb = self.encode_referentiel().astype("float32")
        faiss.normalize_L2(emb)
        index = faiss.IndexFlatIP(emb.shape[1])
        index.add(emb)
        self._faiss_index = index
        logger.info(f"Index FAISS construit: {index.ntotal} vecteurs")
        return index

    def faiss_search(self, query_text: str, top_n: int = 3) -> List[Tuple[int, float]]:
        """Recherche les top-N via FAISS si disponible, sinon cosinus dense."""
        if self._faiss_index is None:
            self.build_faiss_index()
        if self._faiss_index is None:  # FAISS absent → repli
            sims = self.calculate_similarity(self.encode_text(query_text),
                                             self.encode_referentiel())
            return self.get_top_matches(sims, top_n)
        import faiss
        q = self.encode_text(query_text).astype("float32").reshape(1, -1)
        faiss.normalize_L2(q)
        scores, idx = self._faiss_index.search(q, top_n)
        return [(int(i), float(s)) for i, s in zip(idx[0], scores[0])]
    
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
