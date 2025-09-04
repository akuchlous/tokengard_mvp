## TokenGuard Architecture and Module Reference

This document provides high-level documentation for the Python modules in the repository: purpose, key classes/functions, and how they interact.

### App entrypoint

- `app.py`
  - Creates the Flask app via `create_app(...)`.
  - Initializes an in-memory database in testing or when `sqlite:///:memory:` is used.
  - Runs the development server when executed directly.

### Flask application factory and configuration

- `app/__init__.py`
  - Exposes `create_app(config_overrides=None)` to build the Flask app.
  - Registers blueprints, database, error handlers, and extensions.

- `app/config/config.py`
  - Central configuration definitions (base, testing, production overrides).
  - Reads environment variables for secrets and DB URIs.

### Routes (HTTP endpoints)

- `app/routes/main.py`
  - Landing page, health checks, and common pages.

- `app/routes/auth.py`
  - Authentication and account flows: registration, activation, login, password reset.
  - Helpers to generate/consume activation and reset tokens.

- `app/routes/api.py`
  - JSON API endpoints (e.g., `/api/proxy`) for LLM proxying and keyword checks.
  - Integrates with policy checks, proxy logger, and cache.

### Models (database layer)

- `app/models/database.py`
  - SQLAlchemy database initialization and common helpers.

- `app/models/user.py`
  - `User` model: id, email, password hash, status, timestamps.
  - Relationships: API keys, banned keywords, activation/reset tokens.

- `app/models/api_key.py`
  - `APIKey` model: user-bound, value/state, last_used, stats helpers.

- `app/models/banned_keyword.py`
  - `BannedKeyword` model: per-user keyword storage and lookups.

- `app/models/proxy_log.py`
  - `ProxyLog` model: logs proxy requests and outcomes for analytics.

- `app/models/utils.py`
  - Model utilities: API key generation, shared helpers.

### Utilities (business logic and helpers)

- `app/utils/auth_utils.py`
  - Password hashing/verification, JWT generation/verification, email utilities.

- `app/utils/api_utils.py`
  - Request validation (JSON shape, API key presence, text), response formatting.
  - Rate limiting and global singletons used in endpoints.

- `app/utils/validators.py`
  - Validation primitives: email/password formats, injection/XSS patterns, sanitization.

- `app/utils/policy_checks.py`
  - `PolicyChecker`: validates API key status, banned keyword policy, external security.
  - Aggregates multiple checks for the `/api/proxy` endpoint.

- `app/utils/cache_lookup.py`
  - `CacheLookup`: in-memory key/value store with TTL, eviction, and stats.
  - `LLMCacheLookup`: semantic cache over embeddings; supports `cache_llm_response` and `get_llm_response` using cosine similarity and thresholding.

- `app/utils/llm_proxy.py`
  - `LLMProxy`: orchestrates policy checks, cache lookup, LLM calls, and response formatting.

- `app/utils/token_counter.py`
  - Token counting and cost estimation utilities for LLM requests.

- `app/utils/token_utils.py`
  - Tokenization helpers and pricing/limits integration.

- `app/utils/error_handlers.py`
  - Flask error handlers returning JSON/HTML according to context.

- `app/utils/prom_metrics.py`
  - Prometheus metrics definitions and the `/metrics` endpoint wiring.

- `app/utils/proxy_logger.py`
  - Log persistence for `/api/proxy` requests to `ProxyLog` and querying helpers.

### Tests

The `tests/` directory includes unit, integration, and e2e-style tests. Notable suites:

- `tests/test_banned_keywords.py`: model and route tests for banned keywords and proxy interaction.
- `tests/test_proxy_endpoint.py`: `/api/proxy` endpoint shape and behavior.
- `tests/test_llm_proxy.py`: `LLMProxy` flow including policy, cache hit/miss, and error handling.
- `tests/test_cache_lookup.py`: core cache behavior (TTL, eviction, stats).
- `tests/test_semantic_cache.py`: semantic cache hit/miss, similarity thresholds.
- `tests/test_policy_checks.py`: policy checker coverage for API keys, content rules, and external checks.

### Execution flow (simplified)

1. Client calls `/api/proxy` with `api_key` and `text`.
2. `PolicyChecker` validates API key, banned keywords, and security checks.
3. `LLMCacheLookup` is queried for a semantic hit; if found, return cached.
4. If miss, `LLMProxy` calls the configured LLM provider, logs the request, and caches the response via `cache_llm_response`.
5. Response is formatted and returned; Prometheus metrics and logs are updated.


