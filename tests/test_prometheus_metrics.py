import re


def test_metrics_endpoint_exposes_prometheus(app):
    with app.test_client() as client:
        resp = client.get('/api/metrics')
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        # Basic presence of our metric names
        assert 'tg_http_requests_total' in body
        assert 'tg_cache_lookups_total' in body
        # Check content type
        assert resp.mimetype.startswith('text/plain')

