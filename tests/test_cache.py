"""Tests du gestionnaire de cache GenAI (limitation des coûts API)."""

from src.cache_manager import CacheManager


def test_set_get(tmp_path):
    c = CacheManager(cache_dir=str(tmp_path / "c"), max_size=10)
    assert c.get("prompt A", model="m") is None
    c.set("prompt A", "réponse A", model="m")
    assert c.get("prompt A", model="m") == "réponse A"


def test_cle_depend_du_modele(tmp_path):
    c = CacheManager(cache_dir=str(tmp_path / "c"), max_size=10)
    c.set("p", "r1", model="m1")
    # Même prompt, modèle différent -> pas de collision
    assert c.get("p", model="m2") is None
    assert c.get("p", model="m1") == "r1"


def test_eviction_fifo(tmp_path):
    c = CacheManager(cache_dir=str(tmp_path / "c"), max_size=2)
    c.set("p1", "r1", model="m")
    c.set("p2", "r2", model="m")
    c.set("p3", "r3", model="m")  # évince p1 (FIFO)
    assert c.get("p1", model="m") is None
    assert c.get("p3", model="m") == "r3"


def test_persistance_disque(tmp_path):
    d = str(tmp_path / "c")
    c1 = CacheManager(cache_dir=d, max_size=10)
    c1.set("p", "r", model="m")
    # Nouvelle instance -> recharge depuis le fichier
    c2 = CacheManager(cache_dir=d, max_size=10)
    assert c2.get("p", model="m") == "r"


def test_disabled_ne_cache_pas(tmp_path):
    c = CacheManager(cache_dir=str(tmp_path / "c"), max_size=10, enabled=False)
    c.set("p", "r", model="m")
    assert c.get("p", model="m") is None


def test_stats(tmp_path):
    c = CacheManager(cache_dir=str(tmp_path / "c"), max_size=5)
    c.set("p", "r", model="m")
    s = c.get_stats()
    assert s["entries"] == 1 and s["max_size"] == 5 and s["enabled"] is True
