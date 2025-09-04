import pytest
import numpy as np

from app.utils.cache_lookup import LLMCacheLookup, CacheLookup


class DummyModel:
    """Deterministic dummy embedding model for tests."""
    def encode(self, texts, normalize_embeddings=False):
        vecs = []
        for t in texts:
            t = (t or "").lower()
            if any(kw in t for kw in ["delete account", "remove user profile", "close my account", "deactivate profile"]):
                vecs.append(np.array([1.0, 0.0, 0.0, 0.0]))
            elif any(kw in t for kw in ["weather", "forecast", "temperature"]):
                vecs.append(np.array([0.0, 1.0, 0.0, 0.0]))
            else:
                vecs.append(np.array([0.0, 0.0, 1.0, 0.0]))
        return np.stack(vecs, axis=0)


@pytest.fixture
def semantic_cache():
    cache = CacheLookup()
    llm_cache = LLMCacheLookup(cache_lookup=cache, similarity_threshold=0.89)
    # Inject dummy model without downloading real model
    llm_cache._model = DummyModel()
    return llm_cache


def test_semantic_cache_hit_for_similar_prompts(semantic_cache):
    api_key = "tk-test-key"
    # Seed cache with a prompt/response
    seed_request = {"api_key": api_key, "text": "delete account now"}
    seed_response = {"ok": True, "response": {"choices": [{"message": {"content": "Deleted."}}]}}
    assert semantic_cache.cache_llm_response(api_key, seed_request, seed_response, ttl=3600) is True

    # Query with a semantically similar prompt
    query_request = {"api_key": api_key, "text": "please remove user profile"}
    found, cached = semantic_cache.get_llm_response(api_key, query_request)
    assert found is True
    assert isinstance(cached.get("similarity"), float)
    assert cached["similarity"] >= 0.89


def test_semantic_cache_miss_for_unrelated_prompts(semantic_cache):
    api_key = "tk-test-key"
    seed_request = {"api_key": api_key, "text": "delete account now"}
    seed_response = {"ok": True, "response": {"choices": [{"message": {"content": "Deleted."}}]}}
    assert semantic_cache.cache_llm_response(api_key, seed_request, seed_response, ttl=3600) is True

    # Unrelated topic should miss
    query_request = {"api_key": api_key, "text": "what's the weather today?"}
    found, cached = semantic_cache.get_llm_response(api_key, query_request)
    assert found is False


def test_semantic_cache_hit_for_close_my_account(semantic_cache):
    api_key = "tk-test-key"
    seed_request = {"api_key": api_key, "text": "delete account now"}
    seed_response = {"ok": True, "response": {"choices": [{"message": {"content": "Deleted."}}]}}
    assert semantic_cache.cache_llm_response(api_key, seed_request, seed_response, ttl=3600) is True

    query_request = {"api_key": api_key, "text": "please CLOSE my account immediately"}
    found, cached = semantic_cache.get_llm_response(api_key, query_request)
    assert found is True
    assert cached["similarity"] >= 0.89


def test_semantic_cache_hit_for_deactivate_profile(semantic_cache):
    api_key = "tk-test-key"
    seed_request = {"api_key": api_key, "text": "close my account"}
    seed_response = {"ok": True, "response": {"choices": [{"message": {"content": "Closed."}}]}}
    assert semantic_cache.cache_llm_response(api_key, seed_request, seed_response, ttl=3600) is True

    query_request = {"api_key": api_key, "text": "how to deactivate profile?"}
    found, cached = semantic_cache.get_llm_response(api_key, query_request)
    assert found is True
    assert cached["similarity"] >= 0.89


def test_semantic_cache_hit_for_remove_user_profile_variant(semantic_cache):
    api_key = "tk-test-key"
    seed_request = {"api_key": api_key, "text": "please remove user profile"}
    seed_response = {"ok": True, "response": {"choices": [{"message": {"content": "Removed."}}]}}
    assert semantic_cache.cache_llm_response(api_key, seed_request, seed_response, ttl=3600) is True

    query_request = {"api_key": api_key, "text": "can you remove USER PROFILE permanently?"}
    found, cached = semantic_cache.get_llm_response(api_key, query_request)
    assert found is True
    assert cached["similarity"] >= 0.89


def test_semantic_cache_hit_for_weather_variants(semantic_cache):
    api_key = "tk-test-key"
    seed_request = {"api_key": api_key, "text": "weather forecast"}
    seed_response = {"ok": True, "response": {"choices": [{"message": {"content": "Sunny."}}]}}
    assert semantic_cache.cache_llm_response(api_key, seed_request, seed_response, ttl=3600) is True

    query_request = {"api_key": api_key, "text": "TEMPERATURE and forecast today"}
    found, cached = semantic_cache.get_llm_response(api_key, query_request)
    assert found is True
    assert cached["similarity"] >= 0.89


def test_semantic_cache_hit_for_exact_vector_match_is_one(semantic_cache):
    api_key = "tk-test-key"
    seed_request = {"api_key": api_key, "text": "delete account"}
    seed_response = {"ok": True, "response": {"choices": [{"message": {"content": "Deleted."}}]}}
    assert semantic_cache.cache_llm_response(api_key, seed_request, seed_response, ttl=3600) is True

    query_request = {"api_key": api_key, "text": "delete account"}
    found, cached = semantic_cache.get_llm_response(api_key, query_request)
    assert found is True
    assert cached["similarity"] == 1.0


def test_semantic_cache_score_around_point_five():
    class MidModel:
        def encode(self, texts, normalize_embeddings=False):
            vecs = []
            for t in texts:
                t = (t or "").lower()
                if "seed" in t:
                    vecs.append(np.array([1.0, 0.0, 0.0, 0.0]))
                elif "half" in t:
                    vecs.append(np.array([0.5, np.sqrt(1.0 - 0.25), 0.0, 0.0]))  # cosine ~ 0.5 vs seed
                else:
                    vecs.append(np.array([0.0, 0.0, 1.0, 0.0]))
            return np.stack(vecs, axis=0)

    cache = CacheLookup()
    llm_cache = LLMCacheLookup(cache_lookup=cache, similarity_threshold=0.49)
    llm_cache._model = MidModel()

    api_key = "tk-test-key"
    seed_req = {"api_key": api_key, "text": "seed"}
    seed_resp = {"ok": True, "response": {"choices": [{"message": {"content": "ok"}}]}}
    assert llm_cache.cache_llm_response(api_key, seed_req, seed_resp, ttl=3600)

    query_req = {"api_key": api_key, "text": "half similar"}
    found, cached = llm_cache.get_llm_response(api_key, query_req)
    assert found is True
    assert pytest.approx(cached["similarity"], rel=1e-3, abs=1e-3) == 0.5


def test_semantic_cache_score_around_point_one():
    class LowModel:
        def encode(self, texts, normalize_embeddings=False):
            vecs = []
            for t in texts:
                t = (t or "").lower()
                if "seed" in t:
                    vecs.append(np.array([1.0, 0.0, 0.0, 0.0]))
                elif "tiny" in t:
                    vecs.append(np.array([0.1, np.sqrt(1.0 - 0.01), 0.0, 0.0]))  # cosine ~ 0.1 vs seed
                else:
                    vecs.append(np.array([0.0, 0.0, 1.0, 0.0]))
            return np.stack(vecs, axis=0)

    cache = CacheLookup()
    llm_cache = LLMCacheLookup(cache_lookup=cache, similarity_threshold=0.09)
    llm_cache._model = LowModel()

    api_key = "tk-test-key"
    seed_req = {"api_key": api_key, "text": "seed"}
    seed_resp = {"ok": True, "response": {"choices": [{"message": {"content": "ok"}}]}}
    assert llm_cache.cache_llm_response(api_key, seed_req, seed_resp, ttl=3600)

    query_req = {"api_key": api_key, "text": "tiny overlap"}
    found, cached = llm_cache.get_llm_response(api_key, query_req)
    assert found is True
    assert pytest.approx(cached["similarity"], rel=1e-3, abs=1e-3) == 0.1

