import json
import numpy as np


def test_update_similarity_threshold_requires_auth(client):
    # Endpoint no longer accepts POST; ensure unauth GET still requires auth
    r = client.get('/user/some-user')
    assert r.status_code == 401


def test_similarity_threshold_update_and_cache_behavior(app, client, db_session):
    # Create a user
    from app.models.user import User
    from app.models import db
    # Provide a valid 64-char hex password hash
    u = User(email='st@test.com', password_hash='a'*64)
    u.status = 'active'
    db.session.add(u)
    db.session.commit()

    user_id = u.user_id

    # Log in session
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    # Ensure we control the embedding model
    from app.utils.cache_lookup import llm_cache_lookup

    class MidModel:
        def encode(self, texts, normalize_embeddings=False):
            vecs = []
            for t in texts:
                t = (t or '').lower()
                if 'seed' in t:
                    vecs.append(np.array([1.0, 0.0, 0.0, 0.0]))
                elif 'half' in t:
                    # cosine ~ 0.5 vs seed
                    vecs.append(np.array([0.5, np.sqrt(1.0 - 0.25), 0.0, 0.0]))
                else:
                    vecs.append(np.array([0.0, 0.0, 1.0, 0.0]))
            return np.stack(vecs, axis=0)

    # Swap in deterministic model
    llm_cache_lookup._model = MidModel()

    # Seed cache for this user scope with text 'seed'
    seed_request = {'api_key': user_id, 'text': 'seed'}
    seed_response = {'ok': True, 'response': {'choices': [{'message': {'content': 'ok'}}]}}
    assert llm_cache_lookup.cache_llm_response(user_id, seed_request, seed_response, ttl=3600)

    # Query with ~0.5 similarity - default threshold is instance default (keep high)
    query_request = {'api_key': user_id, 'text': 'half similar'}
    found, cached = llm_cache_lookup.get_llm_response(user_id, query_request)
    # With default threshold (>= 0.75 typical), should be miss
    assert found is False

    # Update threshold directly via backend setter (UI removed)
    llm_cache_lookup.set_user_similarity_threshold(user_id, 0.49)
    assert abs(llm_cache_lookup.get_user_similarity_threshold(user_id) - 0.49) < 1e-6

    # Now it should be a hit
    found2, cached2 = llm_cache_lookup.get_llm_response(user_id, query_request)
    assert found2 is True
    assert isinstance(cached2, dict)


