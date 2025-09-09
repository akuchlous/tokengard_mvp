"""
JSON API routes.

Provides `/api/proxy` for LLM proxying, returning structured JSON responses.
Relies on `api_utils` for validation/formatting, `policy_checks` for safety,
`llm_proxy` for orchestration, and `proxy_logger` for persistence.
"""
"""
API Routes

FLOW OVERVIEW
- /api/proxy [POST]
  • Validates request and policies, performs semantic cache lookup, calls LLM on miss, logs/metrics.
  • Policy-only mode supported via request flag.
- /api/cache/*
  • Stats/clear/invalidate per-user cache.
- /api/clear-database [POST]
  • Test/dev-only database reset with confirmation token and guardrails.
- Misc helpers (e.g., health, auth-related test utilities when enabled).
"""

from flask import Blueprint, jsonify, request, url_for, current_app, Response
from ..models import User, APIKey, ActivationToken, ProxyLog, BannedKeyword, db
import json
import time
import uuid
import os
from datetime import datetime
from ..utils.prom_metrics import metrics_latest, CONTENT_TYPE_LATEST
from ..utils.cache_lookup import llm_cache_lookup
from ..models import ProxyLog

api_bp = Blueprint('api', __name__)

def check_external_api(text):
    """
    Placeholder function for external API content checking.
    
    This is where you would integrate with external services like:
    - Content moderation APIs
    - Spam detection services
    - Toxicity detection APIs
    - Custom ML models
    
    Args:
        text (str): The text content to check
        
    Returns:
        dict: {
            'blocked': bool,
            'reason': str,
            'confidence': float,
            'service': str
        }
        
    Raises:
        Exception: If external API call fails
    """
    try:
        # Input validation
        if not isinstance(text, str):
            raise ValueError("Text must be a string")
        
        # TODO: Implement actual external API call
        # For now, this is a placeholder that simulates external checking
        
        # Simulate some basic checks
        if not text or len(text.strip()) == 0:
            return {
                'blocked': False,
                'reason': 'No content to check',
                'confidence': 1.0,
                'service': 'placeholder'
            }
        
        # Simulate blocking very long text (over 1000 characters)
        if len(text) > 1000:
            return {
                'blocked': True,
                'reason': 'Content too long',
                'confidence': 0.8,
                'service': 'placeholder'
            }
        
        # Simulate blocking text with excessive repetition
        words = text.lower().split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            max_repetition = max(word_counts.values()) if word_counts else 0
            if max_repetition > len(words) * 0.3:  # More than 30% repetition
                return {
                    'blocked': True,
                    'reason': 'Excessive word repetition detected',
                    'confidence': 0.7,
                    'service': 'placeholder'
                }
        
        # If all checks pass
        return {
            'blocked': False,
            'reason': 'Content passed external checks',
            'confidence': 0.9,
            'service': 'placeholder'
        }
        
    except Exception as e:
        # Log the error and re-raise for proper handling in the calling function
        current_app.logger.error(f"External API check failed: {str(e)}")
        raise

@api_bp.route('/get-activation-link/<email>')
def get_activation_link(email):
    """Get activation link for a given email (for demo purposes)"""
    try:
        # Find user by email
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Find the most recent valid activation token for this user
        activation_token = ActivationToken.query.filter_by(
            user_id=user.id,
            used=False
        ).order_by(ActivationToken.created_at.desc()).first()
        
        if not activation_token:
            return jsonify({'error': 'No valid activation token found'}), 404
        
        # Construct the activation URL
        activation_url = url_for('auth.activate_account', token=activation_token.token, _external=True)
        
        return jsonify({
            'email': email,
            'activation_url': activation_url,
            'token': activation_token.token
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/status')
def api_status():
    """API status endpoint"""
    import os
    return jsonify({
        'status': 'operational',
        'version': '1.0.0',
        'environment': os.getenv('FLASK_ENV', 'development')
    })

@api_bp.route('/session-debug')
def session_debug():
    """Debug endpoint to check session state"""
    from flask import session
    
    response_data = {
        'session_data': dict(session),
        'has_user_id': 'user_id' in session,
        'user_id': session.get('user_id'),
        'user_email': session.get('user_email'),
        'cookies': dict(request.cookies),
        'headers': dict(request.headers)
    }
    
    # If user is logged in, also check their API keys
    if 'user_id' in session:
        user = User.query.filter_by(user_id=session['user_id']).first()
        if user:
            api_keys = APIKey.query.filter_by(user_id=user.id).all()
            response_data['api_keys_count'] = len(api_keys)
            response_data['api_keys'] = [
                {
                    'id': key.id,
                    'key_name': key.key_name,
                    'key_value': key.key_value,
                    'state': key.state
                }
                for key in api_keys
            ]
    
    return jsonify(response_data)


@api_bp.route('/logs/<proxy_id>', methods=['GET'])
def get_proxy_log_by_id(proxy_id):
    """Fetch a single proxy log by `proxy_id` (UUID request_id) or numeric DB id.

    SECURITY: Requires a valid API key belonging to the owner of the log.
    Accepts API key via JSON body (api_key), query (?api_key=), or X-API-Key header.
    """
    try:
        # Find the log by UUID request_id or numeric id
        log = None
        try:
            # Try UUID match on request_id
            log = ProxyLog.query.filter_by(request_id=str(proxy_id)).first()
        except Exception:
            log = None
        if not log:
            # Fallback: if numeric, try DB id
            try:
                numeric_id = int(proxy_id)
                log = ProxyLog.query.filter_by(id=numeric_id).first()
            except Exception:
                log = None
        if not log:
            return jsonify({'error': 'Log not found'}), 404

        # Extract api_key from multiple places
        api_key = None
        if request.is_json:
            data = request.get_json(silent=True) or {}
            api_key = (data.get('api_key') or '').strip()
        if not api_key:
            api_key = (request.args.get('api_key') or '').strip()
        if not api_key:
            api_key = (request.headers.get('X-API-Key') or '').strip()

        if not api_key:
            return jsonify({'error': 'API key required'}), 401

        # Validate API key and authorize access to the log
        from ..utils.policy_checks import policy_checker
        result = policy_checker.validate_api_key(api_key)
        if not result.passed:
            return jsonify({'error': 'Invalid or inactive API key', 'code': result.error_code}), 401

        user = result.details['user']
        # Ensure the log belongs to this user's keys
        from ..models import APIKey
        user_keys = APIKey.query.filter_by(user_id=user.id).all()
        user_key_values = {k.key_value for k in user_keys}
        if log.api_key_value not in user_key_values:
            return jsonify({'error': 'Access denied for this log'}), 403

        # Attach cache details (if any) by parsing response body
        log_dict = log.to_dict()
        # Prefer cache_info extracted from stored response_body; otherwise try raw stored log
        cache_info = None
        try:
            rb = json.loads(log_dict.get('response_body') or '{}')
            cache_info = rb.get('cache_info')
        except Exception:
            cache_info = None
        if not cache_info:
            try:
                rb2 = json.loads(log.response_body or '{}') if hasattr(log, 'response_body') else {}
                cache_info = rb2.get('cache_info')
            except Exception:
                cache_info = None
        if not cache_info:
            try:
                # Some code paths log an already-enriched payload
                parsed_logged = json.loads(log.request_body or '{}')
                if isinstance(parsed_logged, dict) and 'cache_info' in parsed_logged:
                    cache_info = parsed_logged['cache_info']
            except Exception:
                pass
        if cache_info:
            log_dict['cache_info'] = cache_info
        return jsonify(log_dict), 200
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve log: {str(e)}'}), 500

@api_bp.route('/v1/chat/completions', methods=['POST'])
@api_bp.route('/proxy', methods=['POST'])
def proxy_endpoint():
    """
    LLM Proxy endpoint that processes requests through the proxy architecture.
    
    FEATURES:
    - Policy validation (API key, banned keywords, security checks)
    - Cache lookup for existing responses
    - LLM service integration (stub implementation)
    - Comprehensive logging and metrics
    - Rate limiting and security monitoring
    
    Expects JSON payload with:
    - api_key: The API key to validate (required)
    - text: The text to process (optional, max 10KB)
    - model: LLM model to use (optional, default: 'default')
    - temperature: Temperature setting (optional, default: 0.7)
    
    Returns:
    - {"success": true, "data": {...}} if successful
    - {"success": false, "error_code": "...", "message": "..."} if failed
    """
    # Get request metadata
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
    user_agent = request.headers.get('User-Agent')
    
    # Use shared validation utilities
    from ..utils.api_utils import request_validator, rate_limiter, response_formatter
    
    # SECURITY CHECK 1: Request size limit
    is_valid_size, size_error = request_validator.validate_request_size(client_ip)
    if not is_valid_size:
        return jsonify(size_error), 413
    
    # SECURITY CHECK 2: Rate limiting
    is_allowed, rate_error = rate_limiter.check_rate_limit(client_ip)
    if not is_allowed:
        return jsonify(rate_error), 429
    
    # Validate JSON request
    is_valid_json, data, json_error = request_validator.validate_json_request(client_ip)
    if not is_valid_json:
        return jsonify(json_error), 400
    # Accept "message" as alias for "text" (legacy test UI) OR accept OpenAI-style messages array.
    try:
        if 'messages' in data and isinstance(data['messages'], list):
            # Derive text for policy/cache from user messages concatenation
            joined = []
            for m in data['messages']:
                try:
                    if isinstance(m, dict) and m.get('role') == 'user' and isinstance(m.get('content'), str):
                        joined.append(m.get('content'))
                except Exception:
                    continue
            derived_text = ('\n\n'.join(joined)).strip()
            if derived_text:
                data['text'] = derived_text
        elif 'text' not in data and isinstance(data.get('message'), str):
            data['text'] = data['message']
    except Exception:
        pass
    
    # Validate API key
    is_valid_key, api_key, key_error = request_validator.validate_api_key(data, client_ip)
    if not is_valid_key:
        return jsonify(key_error), 400
    # Ensure downstream components receive the validated key even if it arrived via header
    # so that proxy processing (which reads from request_data) is consistent.
    data['api_key'] = api_key
    
    # Default: policy-only unless explicitly disabled
    try:
        if 'policy_only' not in data:
            data['policy_only'] = True
    except Exception:
        data['policy_only'] = True

    # Process request through LLM proxy
    from ..utils.llm_proxy import llm_proxy
    
    try:
        proxy_response = llm_proxy.process_request(data, client_ip, user_agent)
        
        # Convert to appropriate response format
        return jsonify(proxy_response.to_dict()), proxy_response.status_code
            
    except Exception as e:
        current_app.logger.error(f"Error in proxy endpoint: {str(e)}", exc_info=True)
        error_response = response_formatter.format_server_error_response()
        return jsonify(error_response), 500


@api_bp.route('/metrics')
def metrics():
    """Prometheus metrics endpoint."""
    output = metrics_latest()
    return Response(output, mimetype=CONTENT_TYPE_LATEST)


@api_bp.route('/ttl/<api_key>', methods=['GET'])
def get_user_ttl(api_key):
    """Get per-user cache TTL (seconds). Default is 30 days if not set."""
    try:
        from ..utils.policy_checks import policy_checker
        policy_result = policy_checker.validate_api_key(api_key)
        if not policy_result.passed:
            return jsonify({
                'success': False,
                'error_code': policy_result.error_code,
                'message': policy_result.message
            }), 401
        user = policy_result.details['user']
        user_scope = getattr(user, 'user_id', None) or str(user.id)
        ttl_seconds = llm_cache_lookup.cache_lookup.get_user_ttl(user_scope)
        return jsonify({'success': True, 'data': {'user_id': user_scope, 'ttl_seconds': ttl_seconds}}), 200
    except Exception as e:
        return jsonify({'success': False, 'error_code': 'TTL_GET_ERROR', 'message': str(e)}), 500


@api_bp.route('/ttl/<api_key>', methods=['POST'])
def set_user_ttl(api_key):
    """Set per-user cache TTL (seconds). Body: { ttl_seconds: int }"""
    try:
        from ..utils.policy_checks import policy_checker
        from ..utils.api_utils import request_validator
        policy_result = policy_checker.validate_api_key(api_key)
        if not policy_result.passed:
            return jsonify({
                'success': False,
                'error_code': policy_result.error_code,
                'message': policy_result.message
            }), 401
        is_valid, data, error = request_validator.validate_json_request()
        if not is_valid:
            return jsonify(error), 400
        ttl_seconds = int(data.get('ttl_seconds', 0))
        if ttl_seconds <= 0:
            return jsonify({'success': False, 'error_code': 'INVALID_TTL', 'message': 'ttl_seconds must be > 0'}), 400
        user = policy_result.details['user']
        user_scope = getattr(user, 'user_id', None) or str(user.id)
        llm_cache_lookup.cache_lookup.set_user_ttl(user_scope, ttl_seconds)
        return jsonify({'success': True, 'data': {'user_id': user_scope, 'ttl_seconds': ttl_seconds}}), 200
    except Exception as e:
        return jsonify({'success': False, 'error_code': 'TTL_SET_ERROR', 'message': str(e)}), 500


@api_bp.route('/logs', methods=['GET'])
def get_proxy_logs():
    """
    Get proxy logs for the authenticated user's API keys.
    
    Query parameters:
    - limit: Number of logs to return (default: 100, max: 1000)
    - offset: Number of logs to skip (default: 0)
    - start_date: Start date filter (ISO format)
    - end_date: End date filter (ISO format)
    - api_key: Filter by specific API key value
    """
    from flask import session
    
    # Check if user is authenticated
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Get authenticated user
    user = User.query.filter_by(user_id=session['user_id']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get query parameters
    limit = min(int(request.args.get('limit', 100)), 1000)  # Cap at 1000
    offset = int(request.args.get('offset', 0))
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    api_key_filter = request.args.get('api_key')
    
    # Parse dates if provided
    start_datetime = None
    end_datetime = None
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid start_date format. Use ISO format.'}), 400
    
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid end_date format. Use ISO format.'}), 400
    
    try:
        if api_key_filter:
            # Filter by specific API key (must belong to user)
            from ..models import APIKey
            key_record = APIKey.query.filter_by(
                key_value=api_key_filter,
                user_id=user.id
            ).first()
            
            if not key_record:
                return jsonify({'error': 'API key not found or access denied'}), 404
            
            logs = ProxyLog.get_logs_by_api_key(
                api_key_filter, 
                limit=limit, 
                offset=offset,
                start_date=start_datetime,
                end_date=end_datetime
            )
        else:
            # Get logs for all user's API keys
            logs = ProxyLog.get_logs_by_user(
                user.id,
                limit=limit,
                offset=offset,
                start_date=start_datetime,
                end_date=end_datetime
            )
        
        # Convert logs to dictionary format
        logs_data = [log.to_dict() for log in logs]
        
        return jsonify({
            'logs': logs_data,
            'count': len(logs_data),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve logs: {str(e)}'}), 500


@api_bp.route('/logs/stats', methods=['GET'])
def get_log_stats():
    """
    Get statistics for the authenticated user's API key usage.
    
    Query parameters:
    - days: Number of days to include in stats (default: 30)
    """
    from flask import session
    
    # Check if user is authenticated
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Get authenticated user
    user = User.query.filter_by(user_id=session['user_id']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get query parameters
    days = int(request.args.get('days', 30))
    
    try:
        stats = ProxyLog.get_log_stats_by_user(user.id, days=days)
        
        return jsonify({
            'stats': stats,
            'period_days': days
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve stats: {str(e)}'}), 500


@api_bp.route('/logs/search', methods=['POST'])
def search_logs():
    """
    Search proxy logs with advanced filtering.
    
    Expects JSON payload with search criteria:
    - api_key: Filter by specific API key value
    - status: Filter by response status ('key_pass' or 'key_error')
    - start_date: Start date filter (ISO format)
    - end_date: End date filter (ISO format)
    - limit: Number of results (default: 100, max: 1000)
    - offset: Number of results to skip (default: 0)
    """
    from flask import session
    
    # Check if user is authenticated
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Get authenticated user
    user = User.query.filter_by(user_id=session['user_id']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get search criteria from request
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON payload required'}), 400
    
    api_key_filter = data.get('api_key')
    status_filter = data.get('status')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    limit = min(int(data.get('limit', 100)), 1000)
    offset = int(data.get('offset', 0))
    
    # Parse dates if provided
    start_datetime = None
    end_datetime = None
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid start_date format. Use ISO format.'}), 400
    
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid end_date format. Use ISO format.'}), 400
    
    try:
        if api_key_filter:
            # Verify API key belongs to user
            from ..models import APIKey
            key_record = APIKey.query.filter_by(
                key_value=api_key_filter,
                user_id=user.id
            ).first()
            
            if not key_record:
                return jsonify({'error': 'API key not found or access denied'}), 404
            
            # Get logs for specific API key
            logs = ProxyLog.get_logs_by_api_key(
                api_key_filter,
                limit=limit,
                offset=offset,
                start_date=start_datetime,
                end_date=end_datetime
            )
        else:
            # Get logs for all user's API keys
            logs = ProxyLog.get_logs_by_user(
                user.id,
                limit=limit,
                offset=offset,
                start_date=start_datetime,
                end_date=end_datetime
            )
        
        # Apply status filter if provided
        if status_filter and status_filter in ['key_pass', 'key_error']:
            logs = [log for log in logs if log.response_status == status_filter]
        
        # Convert logs to dictionary format
        logs_data = [log.to_dict() for log in logs]
        
        return jsonify({
            'logs': logs_data,
            'count': len(logs_data),
            'filters': {
                'api_key': api_key_filter,
                'status': status_filter,
                'start_date': start_date,
                'end_date': end_date
            },
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to search logs: {str(e)}'}), 500



@api_bp.route('/banned-keywords/populate-defaults', methods=['POST'])
def populate_default_keywords():
    """Populate default banned keywords for the authenticated user."""
    from flask import session
    
    # Check if user is authenticated
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Get authenticated user
    user = User.query.filter_by(user_id=session['user_id']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Clear existing keywords first
        BannedKeyword.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        
        added_count = BannedKeyword.populate_default_keywords(user.id)
        return jsonify({
            'message': f'Added {added_count} default keywords',
            'added_count': added_count
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to populate default keywords: {str(e)}'}), 500

@api_bp.route('/banned-keywords/bulk-update', methods=['POST'])
def bulk_update_keywords():
    """Update all banned keywords for the authenticated user from text input."""
    from flask import session
    import re
    
    # Check if user is authenticated
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Get authenticated user
    user = User.query.filter_by(user_id=session['user_id']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get keywords text from request
    data = request.get_json()
    if not data or 'keywords_text' not in data:
        return jsonify({'error': 'Keywords text is required'}), 400
    
    keywords_text = data['keywords_text'].strip()
    if not keywords_text:
        return jsonify({'error': 'Keywords text cannot be empty'}), 400
    
    try:
        # Parse keywords from text (split by spaces and commas)
        keywords = re.split(r'[,\s]+', keywords_text)
        keywords = [kw.strip().lower() for kw in keywords if kw.strip()]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen and len(kw) <= 100:  # Validate length
                seen.add(kw)
                unique_keywords.append(kw)
        
        if not unique_keywords:
            return jsonify({'error': 'No valid keywords found'}), 400
        
        # Clear existing keywords
        BannedKeyword.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        
        # Add new keywords
        saved_count = 0
        for keyword in unique_keywords:
            banned_keyword = BannedKeyword(
                user_id=user.id,
                keyword=keyword
            )
            db.session.add(banned_keyword)
            saved_count += 1
        
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully saved {saved_count} keywords',
            'saved_count': saved_count
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to update keywords: {str(e)}'}), 500


@api_bp.route('/clear-database', methods=['POST'])
def clear_database():
    """
    Clear all data from the database (for testing/demo purposes only).
    
    SECURITY SAFEGUARDS:
    - Only available in test/development environments
    - Requires explicit confirmation token
    - Logs all database clearing operations
    - Uses database transactions for safety
    """
    # SECURITY CHECK 1: Environment validation
    app_env = current_app.config.get('ENV', 'development')
    env_var = os.getenv('FLASK_ENV', 'development')
    
    # Block in production environments
    if app_env == 'production' or env_var == 'production':
        current_app.logger.warning(f"Database clear attempt blocked in production environment")
        return jsonify({'error': 'Database clearing not allowed in production'}), 403
    
    # Only allow in explicitly allowed environments
    allowed_envs = ['test', 'testing', 'development']
    if env_var not in allowed_envs and app_env not in allowed_envs:
        current_app.logger.warning(f"Database clear attempt blocked in environment: {env_var}/{app_env}")
        return jsonify({'error': 'Database clearing only allowed in test/development environments'}), 403
    
    # SECURITY CHECK 2: Require confirmation token
    confirmation_token = request.headers.get('X-Confirmation-Token')
    expected_token = os.getenv('DB_CLEAR_TOKEN', 'demo-clear-token-2024')
    
    if not confirmation_token or confirmation_token != expected_token:
        current_app.logger.warning(f"Database clear attempt with invalid/missing confirmation token")
        return jsonify({'error': 'Confirmation token required for database clearing'}), 401
    
    # SECURITY CHECK 3: Rate limiting (basic implementation)
    # In a real app, use Flask-Limiter or similar
    if hasattr(current_app, 'db_clear_attempts'):
        current_app.db_clear_attempts += 1
    else:
        current_app.db_clear_attempts = 1
    
    if current_app.db_clear_attempts > 5:  # Max 5 attempts per app instance
        current_app.logger.error(f"Database clear rate limit exceeded: {current_app.db_clear_attempts} attempts")
        return jsonify({'error': 'Rate limit exceeded for database clearing'}), 429
    
    try:
        # SECURITY CHECK 4: Log the operation
        current_app.logger.info(f"Database clearing initiated by {request.remote_addr} in {env_var} environment")
        
        # Use database transaction for safety
        with db.session.begin():
            # Clear tables in dependency order (foreign keys first)
            cleared_counts = {}
            
            # Clear dependent tables first
            cleared_counts['proxy_logs'] = ProxyLog.query.count()
            ProxyLog.query.delete()
            
            cleared_counts['banned_keywords'] = BannedKeyword.query.count()
            BannedKeyword.query.delete()
            
            cleared_counts['api_keys'] = APIKey.query.count()
            APIKey.query.delete()
            
            cleared_counts['activation_tokens'] = ActivationToken.query.count()
            ActivationToken.query.delete()
            
            cleared_counts['users'] = User.query.count()
            User.query.delete()
        
        # Log successful operation
        current_app.logger.info(f"Database cleared successfully: {cleared_counts}")
        
        return jsonify({
            'message': 'Database cleared successfully',
            'cleared_counts': cleared_counts,
            'environment': {
                'flask_env': app_env,
                'env_var': env_var
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database clear failed: {str(e)}")
        return jsonify({'error': f'Failed to clear database: {str(e)}'}), 500


@api_bp.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get cache statistics for the authenticated user scope."""
    from flask import session
    # Require login
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    # Resolve authenticated user
    user = User.query.filter_by(user_id=session['user_id']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    # Enforce active account
    if not user.is_active():
        return jsonify({'error': 'Account not activated'}), 403
    try:
        from ..utils.llm_proxy import llm_proxy
        # Overall cache stats (system-wide)
        global_stats = llm_proxy.get_cache_stats()
        # Per-user cache info
        user_scope = getattr(user, 'user_id', None) or str(user.id)
        user_info = llm_cache_lookup.cache_lookup.get_user_cache_info(user_scope)
        return jsonify({'global': global_stats, 'user': user_info}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get cache stats: {str(e)}'}), 500


@api_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the cache (for testing/demo purposes only)."""
    # Only allow in test/development environments
    app_env = current_app.config.get('ENV', 'development')
    env_var = os.getenv('FLASK_ENV', 'development')
    
    if app_env == 'production' or env_var == 'production':
        return jsonify({'error': 'Cache clearing not allowed in production'}), 403
    
    allowed_envs = ['test', 'testing', 'development']
    if env_var not in allowed_envs and app_env not in allowed_envs:
        return jsonify({'error': 'Cache clearing only allowed in test/development environments'}), 403
    
    try:
        from ..utils.llm_proxy import llm_proxy
        success = llm_proxy.clear_cache()
        if success:
            return jsonify({'message': 'Cache cleared successfully'}), 200
        else:
            return jsonify({'error': 'Failed to clear cache'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to clear cache: {str(e)}'}), 500


@api_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """Get proxy metrics."""
    try:
        from ..utils.llm_proxy import llm_proxy
        minutes = request.args.get('minutes', 60, type=int)
        metrics = llm_proxy.get_metrics(minutes)
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get metrics: {str(e)}'}), 500


@api_bp.route('/proxy/smoke', methods=['POST'])
def proxy_smoke_test():
    """
    Guarded smoke test for LLM proxy. In non-production environments, executes a
    minimal proxy request. In production, requires X-Confirmation-Token to match
    SMOKE_TEST_TOKEN (env) and will still run a minimal request.
    """
    import os
    from ..utils.llm_proxy import llm_proxy
    from ..utils.api_utils import request_validator

    env = os.getenv('FLASK_ENV', 'development').lower()
    is_production = env == 'production'
    if is_production:
        token = request.headers.get('X-Confirmation-Token')
        expected = os.getenv('SMOKE_TEST_TOKEN', '')
        if not expected or token != expected:
            return jsonify({'error': 'Unauthorized smoke test'}), 401

    # Validate JSON but allow empty to default
    is_valid, data, err = request_validator.validate_json_request(request.remote_addr)
    if not is_valid:
        data = {}

    api_key = data.get('api_key') or request.headers.get('X-API-Key') or ''
    text = data.get('text') or 'Health check: respond with OK.'
    model = data.get('model') or 'gpt-4o'
    temperature = data.get('temperature') if data.get('temperature') is not None else 0.7

    payload = {'api_key': api_key, 'text': text, 'model': model, 'temperature': temperature}

    try:
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        user_agent = request.headers.get('User-Agent')
        resp = llm_proxy.process_request(payload, client_ip, user_agent)
        return jsonify(resp.to_dict()), resp.status_code
    except Exception as e:
        return jsonify({'success': False, 'error_code': 'SMOKE_TEST_ERROR', 'message': str(e)}), 500

@api_bp.route('/cache/invalidate/<api_key>', methods=['POST'])
def invalidate_user_cache(api_key):
    """Invalidate cache for a specific user."""
    try:
        from ..utils.llm_proxy import llm_proxy
        count = llm_proxy.invalidate_user_cache(api_key)
        return jsonify({
            'message': f'Invalidated {count} cache entries for user',
            'invalidated_count': count
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to invalidate user cache: {str(e)}'}), 500


## (Removed) Dedicated policy endpoint; use /api/proxy or /v1/chat/completions with policy_only
