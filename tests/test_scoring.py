"""
Tests unitaires du système de scoring.

Ces tests verrouillent le correctif du bug audité : les composantes genre (30 %)
et mood (20 %) doivent réellement varier avec les préférences utilisateur, malgré
les divergences d'accents et de séparateurs entre le questionnaire et le CSV.
Lancer : pytest -q
"""

import numpy as np
import pytest

from src.scoring import ScoringSystem, _normalize, _split_tokens


@pytest.fixture
def scorer():
    return ScoringSystem(alpha=0.50, beta=0.30, gamma=0.20)


def test_poids_normalises():
    s = ScoringSystem(alpha=2, beta=1, gamma=1)
    assert np.isclose(s.alpha + s.beta + s.gamma, 1.0)


def test_normalize_retire_accents():
    assert _normalize("Comédie") == "comedie"
    assert _normalize("Émotionnel/Touchant") == "emotionnel/touchant"


def test_split_tokens_separateurs():
    assert _split_tokens("Drama; Sci-Fi") == ["Drama", " Sci-Fi"]
    assert _split_tokens("Émotionnel/Touchant") == ["Émotionnel", "Touchant"]


def test_genre_match_insensible_accents(scorer):
    """Categorie "Comédie" doit matcher la préférence "Comedie" (sans accent)."""
    weights = {"Comedie": 1.0, "Drame": 0.2}
    assert scorer.calculate_genre_score("Comédie", weights) == 1.0


def test_genre_categorie_francaise(scorer):
    """Avec la bonne colonne (Categorie FR), le score reflète la préférence."""
    weights = {"Science-Fiction": 1.0, "Drame": 0.2, "Thriller": 0.6}
    assert scorer.calculate_genre_score("Science-Fiction", weights) == 1.0
    assert scorer.calculate_genre_score("Drame", weights) == 0.2


def test_genre_colonne_anglaise_etait_le_bug(scorer):
    """Régression : la colonne `Genre` EN ne matche pas (d'où l'usage de Categorie)."""
    weights = {"Science-Fiction": 1.0, "Drame": 0.2}
    # "Drama; Sci-Fi" (anglais) ne correspond à aucune préférence FR -> neutre
    assert scorer.calculate_genre_score("Drama; Sci-Fi", weights) == 0.5


def test_mood_match_insensible_accents(scorer):
    """Mood CSV "Intellectuel/Réflexif" doit matcher "Intellectuel/Reflexif"."""
    weights = {"Intellectuel/Reflexif": 1.0, "Leger/Amusant": 0.2}
    assert scorer.calculate_mood_score("Intellectuel/Réflexif", weights) == 1.0


def test_mood_sans_correspondance_est_neutre(scorer):
    weights = {"Leger/Amusant": 0.8}
    assert scorer.calculate_mood_score("Sombre/Dérangeant", weights) == 0.5


def test_score_final_borne(scorer):
    assert scorer.calculate_final_score(1.0, 1.0, 1.0) == 1.0
    assert scorer.calculate_final_score(0.0, 0.0, 0.0) == 0.0


def test_genre_influence_le_classement(scorer):
    """Preuve fonctionnelle : changer la préférence genre change le score final."""
    rec_sf = {"genre": "Sci-Fi", "categorie": "Science-Fiction",
              "mood": "Intense/Tendu", "score_similarite": 0.6}
    aime_sf = {"Science-Fiction": 1.0, "Romance": 0.2}
    deteste_sf = {"Science-Fiction": 0.2, "Romance": 1.0}
    moods = {"Intense/Tendu": 0.6}

    s_aime = scorer.rank_films([dict(rec_sf)], np.array([0.6]), aime_sf, moods, None)
    s_det = scorer.rank_films([dict(rec_sf)], np.array([0.6]), deteste_sf, moods, None)

    assert s_aime[0]["score_final"] > s_det[0]["score_final"]
