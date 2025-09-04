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

