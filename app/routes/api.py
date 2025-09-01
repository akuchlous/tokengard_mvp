"""
API Routes

This module contains the API endpoints for the application.
"""

from flask import Blueprint, jsonify, request, url_for
from ..models import User, APIKey, ActivationToken, ProxyLog, BannedKeyword
import json
import time
import uuid
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
    """
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
    
    Expects JSON payload with:
    - api_key: The API key to validate
    - text: The text to process (optional)
    
    Returns:
    - {"status": "key_pass", "message": "API key is valid"} if key is active
    - {"status": "key_error", "message": "API key is invalid or inactive"} if key is invalid/inactive
    """
    # Start timing for performance metrics
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Get request metadata for logging
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
    user_agent = request.headers.get('User-Agent')
    
    # Get JSON data from request
    data = request.get_json()
    request_body = json.dumps(data) if data else None
    
    # Initialize response variables
    response_status = 'key_error'
    response_body = None
    response_code = 400
    key_record = None
    
    try:
        if not data:
            response_body = json.dumps({
                'status': 'key_error',
                'message': 'Invalid request format. JSON payload required.'
            })
            response_code = 400
        else:
            # Get API key from either JSON payload or X-API-Key header
            api_key = data.get('api_key', '').strip()
            if not api_key:
                api_key = request.headers.get('X-API-Key', '').strip()
            
            text = data.get('text', '')
            
            # Validate API key is provided
            if not api_key:
                response_body = json.dumps({
                    'status': 'key_error',
                    'message': 'API key is required.'
                })
                response_code = 400
            else:
                # Look up the API key in the database
                key_record = APIKey.query.filter_by(key_value=api_key).first()
                
                if not key_record:
                    response_body = json.dumps({
                        'status': 'key_error',
                        'message': 'API key not found.'
                    })
                    response_code = 401
                elif key_record.state.lower() != 'enabled':
                    response_body = json.dumps({
                        'status': 'key_error',
                        'message': 'API key is inactive.'
                    })
                    response_code = 401
                else:
                    # Key is valid and active - now check content rules
                    user = key_record.user
                    
                    # Check banned keywords
                    if text:
                        is_banned, banned_keyword = BannedKeyword.check_banned(user.id, text)
                        if is_banned:
                            response_body = json.dumps({
                                'status': 'content_error',
                                'message': f'Content contains banned keyword: {banned_keyword}',
                                'banned_keyword': banned_keyword
                            })
                            response_code = 400
                        else:
                            # Placeholder for external API call
                            external_check_result = check_external_api(text)
                            if external_check_result['blocked']:
                                response_body = json.dumps({
                                    'status': 'content_error',
                                    'message': f'Content blocked by external service: {external_check_result["reason"]}',
                                    'external_reason': external_check_result['reason']
                                })
                                response_code = 400
                            else:
                                # Content passed all checks
                                response_status = 'key_pass'
                                response_body = json.dumps({
                                    'status': 'key_pass',
                                    'message': 'API key is valid and content passed all checks.',
                                    'key_name': key_record.key_name,
                                    'text_length': len(text) if text else 0,
                                    'external_check': external_check_result
                                })
                                response_code = 200
                    else:
                        # No text to check, just validate key
                        response_status = 'key_pass'
                        response_body = json.dumps({
                            'status': 'key_pass',
                            'message': 'API key is valid.',
                            'key_name': key_record.key_name,
                            'text_length': 0
                        })
                        response_code = 200
                    
                    # Update last_used timestamp only if request was successful
                    if response_code == 200:
                        key_record.update_last_used()
    
    except Exception as e:
        # Handle any unexpected errors
        response_body = json.dumps({
            'status': 'key_error',
            'message': f'Internal server error: {str(e)}'
        })
        response_code = 500
    
    finally:
        # Calculate processing time
        processing_time_ms = max(1, int((time.time() - start_time) * 1000))  # Ensure at least 1ms
        
        # Log the request/response (only if we have a key record or attempted to use a key)
        if key_record or (data and data.get('api_key')):
            try:
                from ..models import db
                
                # Create log entry
                if key_record:
                    # Valid key record exists
                    log_entry = ProxyLog.create_log(
                        api_key=key_record,
                        request_body=request_body,
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
                        request_body=request_body,
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
                print(f"Warning: Failed to log proxy request: {log_error}")
                from ..models import db
                db.session.rollback()
    
    # Return the response
    return jsonify(json.loads(response_body)) if response_body else jsonify({'status': 'key_error'}), response_code


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
