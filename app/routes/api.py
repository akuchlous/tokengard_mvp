"""
API Routes

This module contains the API endpoints for the application.
"""

from flask import Blueprint, jsonify, request, url_for, current_app
from ..models import User, APIKey, ActivationToken, ProxyLog, BannedKeyword, db
import json
import time
import uuid
import os
from datetime import datetime

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

@api_bp.route('/proxy', methods=['POST'])
def proxy_endpoint():
    """
    Proxy endpoint that validates API key and processes text with comprehensive logging.
    
    SECURITY FEATURES:
    - Input validation and sanitization
    - Rate limiting protection
    - Comprehensive error handling
    - Security logging and monitoring
    - Request size limits
    
    Expects JSON payload with:
    - api_key: The API key to validate (required)
    - text: The text to process (optional, max 10KB)
    
    Returns:
    - {"status": "key_pass", "message": "API key is valid"} if key is active
    - {"status": "key_error", "message": "API key is invalid or inactive"} if key is invalid/inactive
    - {"status": "content_error", "message": "Content blocked"} if content violates rules
    """
    # Start timing for performance metrics
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Get request metadata for logging
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
    user_agent = request.headers.get('User-Agent')
    
    # SECURITY CHECK 1: Request size limit (10KB max)
    content_length = request.content_length or 0
    if content_length > 10240:  # 10KB limit
        current_app.logger.warning(f"Large request blocked from {client_ip}: {content_length} bytes")
        return jsonify({
            'status': 'key_error',
            'message': 'Request too large. Maximum 10KB allowed.',
            'error_code': 'REQUEST_TOO_LARGE'
        }), 413
    
    # SECURITY CHECK 2: Rate limiting (basic implementation)
    # In production, use Flask-Limiter or Redis-based rate limiting
    if not hasattr(current_app, 'proxy_request_counts'):
        current_app.proxy_request_counts = {}
    
    current_time = int(time.time())
    minute_key = f"{client_ip}_{current_time // 60}"
    
    if minute_key in current_app.proxy_request_counts:
        current_app.proxy_request_counts[minute_key] += 1
    else:
        current_app.proxy_request_counts[minute_key] = 1
    
    # Clean old entries (older than 5 minutes)
    old_keys = [k for k in current_app.proxy_request_counts.keys() 
                if int(k.split('_')[-1]) < (current_time // 60) - 5]
    for old_key in old_keys:
        del current_app.proxy_request_counts[old_key]
    
    # Check rate limit (100 requests per minute per IP)
    if current_app.proxy_request_counts[minute_key] > 100:
        current_app.logger.warning(f"Rate limit exceeded for {client_ip}: {current_app.proxy_request_counts[minute_key]} requests")
        return jsonify({
            'status': 'key_error',
            'message': 'Rate limit exceeded. Maximum 100 requests per minute.',
            'error_code': 'RATE_LIMIT_EXCEEDED'
        }), 429
    
    # Get JSON data from request with proper error handling
    try:
        data = request.get_json(force=True)  # Force JSON parsing
    except Exception as e:
        current_app.logger.warning(f"Invalid JSON from {client_ip}: {str(e)}")
        return jsonify({
            'status': 'key_error',
            'message': 'Invalid JSON format. Request must be valid JSON.',
            'error_code': 'INVALID_JSON'
        }), 400
    
    # Initialize response variables
    response_status = 'key_error'
    response_body = None
    response_code = 400
    key_record = None
    
    try:
        if not data:
            current_app.logger.warning(f"Empty request body from {client_ip}")
            return jsonify({
                'status': 'key_error',
                'message': 'Invalid request format. JSON payload required.',
                'error_code': 'MISSING_JSON'
            }), 400
        
        # SECURITY CHECK 3: Input validation and sanitization
        if not isinstance(data, dict):
            current_app.logger.warning(f"Invalid data type from {client_ip}: {type(data)}")
            return jsonify({
                'status': 'key_error',
                'message': 'Request data must be a JSON object.',
                'error_code': 'INVALID_DATA_TYPE'
            }), 400
        
        # Get API key from either JSON payload or X-API-Key header
        api_key = data.get('api_key', '').strip()
        if not api_key:
            api_key = request.headers.get('X-API-Key', '').strip()
        
        text = data.get('text', '')
        
        # SECURITY CHECK 4: API key validation
        if not api_key:
            current_app.logger.warning(f"Missing API key from {client_ip}")
            return jsonify({
                'status': 'key_error',
                'message': 'API key is required. Provide api_key in JSON payload or X-API-Key header.',
                'error_code': 'MISSING_API_KEY'
            }), 400
        
        # SECURITY CHECK 5: API key format validation
        if len(api_key) < 10 or len(api_key) > 200:
            current_app.logger.warning(f"Invalid API key length from {client_ip}: {len(api_key)}")
            return jsonify({
                'status': 'key_error',
                'message': 'API key format is invalid.',
                'error_code': 'INVALID_API_KEY_FORMAT'
            }), 400
        
        # SECURITY CHECK 6: Text content validation
        if text and len(text) > 10000:  # 10KB text limit
            current_app.logger.warning(f"Text too long from {client_ip}: {len(text)} characters")
            return jsonify({
                'status': 'content_error',
                'message': 'Text content too long. Maximum 10,000 characters allowed.',
                'error_code': 'TEXT_TOO_LONG'
            }), 400
        
        # SECURITY CHECK 7: Check for suspicious patterns in API key
        if any(char in api_key for char in ['<', '>', '"', "'", '&', ';', '(', ')']):
            current_app.logger.warning(f"Suspicious API key pattern from {client_ip}")
            return jsonify({
                'status': 'key_error',
                'message': 'API key contains invalid characters.',
                'error_code': 'INVALID_API_KEY_CHARS'
            }), 400
        
        # Look up the API key in the database
        key_record = APIKey.query.filter_by(key_value=api_key).first()
        
        if not key_record:
            current_app.logger.warning(f"API key not found from {client_ip}: {api_key[:10]}...")
            return jsonify({
                'status': 'key_error',
                'message': 'API key not found.',
                'error_code': 'API_KEY_NOT_FOUND'
            }), 401
        elif key_record.state.lower() != 'enabled':
            current_app.logger.warning(f"Inactive API key used from {client_ip}: {api_key[:10]}...")
            return jsonify({
                'status': 'key_error',
                'message': 'API key is inactive.',
                'error_code': 'API_KEY_INACTIVE'
            }), 401
        else:
            # Key is valid and active - now check content rules
            user = key_record.user
            
            # Check if user account is active
            if user.status != 'active':
                current_app.logger.warning(f"Inactive user account from {client_ip}: user_id={user.id}")
                return jsonify({
                    'status': 'key_error',
                    'message': 'User account is inactive.',
                    'error_code': 'USER_ACCOUNT_INACTIVE'
                }), 401
            
            # Check banned keywords
            if text:
                is_banned, banned_keyword = BannedKeyword.check_banned(user.id, text)
                if is_banned:
                    current_app.logger.info(f"Banned keyword detected from {client_ip}: '{banned_keyword}'")
                    return jsonify({
                        'status': 'content_error',
                        'message': f'Content contains banned keyword: {banned_keyword}',
                        'banned_keyword': banned_keyword,
                        'error_code': 'BANNED_KEYWORD'
                    }), 400
                else:
                    # Placeholder for external API call
                    try:
                        external_check_result = check_external_api(text)
                        if external_check_result['blocked']:
                            current_app.logger.info(f"External API blocked content from {client_ip}: {external_check_result['reason']}")
                            return jsonify({
                                'status': 'content_error',
                                'message': f'Content blocked by external service: {external_check_result["reason"]}',
                                'external_reason': external_check_result['reason'],
                                'error_code': 'EXTERNAL_API_BLOCKED'
                            }), 400
                        else:
                            # Content passed all checks
                            response_status = 'key_pass'
                            response_body = json.dumps({
                                'status': 'key_pass',
                                'message': 'API key is valid and content passed all checks.',
                                'key_name': key_record.key_name,
                                'text_length': len(text) if text else 0,
                                'external_check': external_check_result,
                                'request_id': request_id
                            })
                            response_code = 200
                    except Exception as external_error:
                        current_app.logger.error(f"External API check failed from {client_ip}: {str(external_error)}")
                        return jsonify({
                            'status': 'key_error',
                            'message': 'External content check failed. Please try again.',
                            'error_code': 'EXTERNAL_API_ERROR'
                        }), 500
            else:
                # No text to check, just validate key
                response_status = 'key_pass'
                response_body = json.dumps({
                    'status': 'key_pass',
                    'message': 'API key is valid.',
                    'key_name': key_record.key_name,
                    'text_length': 0,
                    'request_id': request_id
                })
                response_code = 200
            
            # Update last_used timestamp only if request was successful
            if response_code == 200:
                try:
                    key_record.update_last_used()
                    db.session.commit()
                except Exception as update_error:
                    current_app.logger.error(f"Failed to update last_used for key {api_key[:10]}...: {str(update_error)}")
                    # Don't fail the request if timestamp update fails
    
    except Exception as e:
        # Handle any unexpected errors
        current_app.logger.error(f"Unexpected error in proxy endpoint from {client_ip}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'key_error',
            'message': 'Internal server error. Please try again later.',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'request_id': request_id
        }), 500
    
    finally:
        # Calculate processing time
        processing_time_ms = max(1, int((time.time() - start_time) * 1000))  # Ensure at least 1ms
        
        # Log the request/response (only if we have a key record or attempted to use a key)
        if key_record or (data and data.get('api_key')):
            try:
                # Create log entry
                if key_record:
                    # Valid key record exists
                    log_entry = ProxyLog.create_log(
                        api_key=key_record,
                        request_body=json.dumps(data) if data else None,
                        response_status=response_status,
                        response_body=response_body,
                        client_ip=client_ip,
                        user_agent=user_agent,
                        request_id=request_id,
                        processing_time_ms=processing_time_ms
                    )
                else:
                    # No key record found, but we want to log the attempt
                    attempted_key = data.get('api_key', '')[:64]  # Truncate if too long
                    log_entry = ProxyLog(
                        api_key_id=None,  # No valid key record
                        api_key_value=attempted_key,
                        request_body=json.dumps(data) if data else None,
                        response_status=response_status,
                        response_body=response_body,
                        client_ip=client_ip,
                        user_agent=user_agent,
                        request_id=request_id,
                        processing_time_ms=processing_time_ms
                    )
                    db.session.add(log_entry)
                
                # Commit the log entry
                db.session.commit()
                
            except Exception as log_error:
                # Don't fail the request if logging fails
                current_app.logger.error(f"Failed to log proxy request: {log_error}")
                db.session.rollback()
    
    # Return the response
    if response_body:
        try:
            return jsonify(json.loads(response_body)), response_code
        except json.JSONDecodeError:
            # Fallback if response_body is not valid JSON
            return jsonify({
                'status': 'key_error',
                'message': 'Invalid response format',
                'error_code': 'INVALID_RESPONSE'
            }), 500
    else:
        return jsonify({
            'status': 'key_error',
            'message': 'No response generated',
            'error_code': 'NO_RESPONSE'
        }), 500


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
