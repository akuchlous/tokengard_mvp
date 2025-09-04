"""
Prometheus metrics registration and helpers.

Exports:
- observe_request(...): record HTTP request metrics
- observe_cache_lookup(...): record cache lookup metrics
- metrics_latest(): return text exposition from correct registry (handles multiprocess)
- CONTENT_TYPE_LATEST: correct Prometheus content type
"""

import os
from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import multiprocess


REQUEST_COUNTER = Counter(
    'tg_http_requests_total', 'Total HTTP requests', ['endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'tg_http_request_latency_seconds', 'HTTP request latency seconds', ['endpoint']
)

CACHE_LOOKUPS = Counter(
    'tg_cache_lookups_total', 'Total cache lookups', ['user_hash']
)

CACHE_HITS = Counter(
    'tg_cache_hits_total', 'Total cache hits', ['user_hash']
)

CACHE_LOOKUP_LATENCY = Histogram(
    'tg_cache_lookup_latency_seconds', 'Cache lookup latency seconds', ['user_hash']
)

CACHE_BEST_SCORE = Histogram(
    'tg_cache_best_similarity_score', 'Best similarity score per lookup', buckets=[
        0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0
    ]
)


def observe_request(endpoint: str, status: int, latency_seconds: float) -> None:
    REQUEST_COUNTER.labels(endpoint=endpoint, status=str(status)).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency_seconds)


def observe_cache_lookup(user_hash: str, lookup_seconds: float, hit: bool, best_score: float) -> None:
    CACHE_LOOKUPS.labels(user_hash=user_hash).inc()
    if hit:
        CACHE_HITS.labels(user_hash=user_hash).inc()
    CACHE_LOOKUP_LATENCY.labels(user_hash=user_hash).observe(lookup_seconds)
    if best_score is not None:
        try:
            CACHE_BEST_SCORE.observe(float(best_score))
        except Exception:
            pass


def metrics_latest() -> bytes:
    """Return the Prometheus text exposition, multiprocess-aware if configured."""
    prom_mp_dir = os.getenv('PROMETHEUS_MULTIPROC_DIR')
    if prom_mp_dir:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry)
    # Default registry
    return generate_latest()


