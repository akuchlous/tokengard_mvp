"""
Main site routes.

Serves index, health/status endpoints, and shared pages. These routes are
lightweight and are used by both users and tests (e.g., availability checks).
"""
"""
Main Routes

FLOW OVERVIEW
- / [GET]
  • Landing page.
- /health [GET]
  • JSON health check.
- /user/<user_id> [GET]
  • Auth gate; self-only profile view.
- /keys/<user_id> [GET]
  • Auth gate; list user's API keys.
- /deactivate-key/<key_id> [POST]
  • Auth gate; deactivate given key if owned.
- /logs/<user_id> [GET]
  • Auth gate; server-side analytics for user's logs.
- /test/<key_value> [GET]
  • Auth gate; UI for trying proxy with a specific key.
- /banned_keywords/<user_id> [GET]
  • Auth gate; manage banned keywords.
- /init-db [GET]
  • Initialize DB tables (dev utility).
"""

from flask import Blueprint, render_template, jsonify, url_for, session, flash, redirect
from datetime import datetime
from ..models import User, APIKey, ProxyLog, BannedKeyword, db
from ..utils.error_handlers import render_error_page

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    """Home page route"""
    return render_template('index.html')

@main_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@main_bp.route('/user/<user_id>')
def user_profile(user_id):
    """User profile route - server-rendered only, user can only view own profile."""
    # Require login
    if 'user_id' not in session:
        return render_error_page('Authentication Required',
            'You need to be logged in to access this page.', 401)

    try:
        # Resolve authenticated user by public user_id stored in session
        authenticated_user = User.query.filter_by(user_id=session['user_id']).first()
        if not authenticated_user:
            return render_error_page('User Not Found',
                'The requested user profile could not be found.', 404)

        # Enforce active status
        if not authenticated_user.is_active():
            return render_error_page('Account Not Activated',
                'This account has not been activated yet.', 403)

        # Enforce self-access
        if authenticated_user.user_id != user_id:
            return render_error_page('Access Denied',
                'You can only view your own profile page.', 403)

        # Prepare data for template
        user_data = {
            'email': authenticated_user.email,
            'user_id': authenticated_user.user_id,
            'status': authenticated_user.status,
            'created_at': authenticated_user.created_at.strftime('%B %d, %Y')
        }
        return render_template('user.html', user=user_data)

    except Exception:
        return render_error_page('Authentication Error',
            'An error occurred while processing your request. Please try again.', 500)

@main_bp.route('/keys/<user_id>')
def user_keys(user_id):
    """Display all API keys for the authenticated user (server-rendered)."""
    # Require login
    if 'user_id' not in session:
        return render_error_page('Authentication Required',
            'You need to be logged in to access this page.', 401)

    # Look up authenticated user by public user_id stored in session
    authenticated_user = User.query.filter_by(user_id=session['user_id']).first()
    if not authenticated_user:
        return render_error_page('User Not Found',
            'The requested user could not be found.', 404)

    # Enforce user can only view their own keys
    if authenticated_user.user_id != user_id:
        return render_error_page('Access Denied',
            'You can only view your own API keys.', 403)

    # Must be active account
    if not authenticated_user.is_active():
        return render_error_page('Account Not Activated',
            'This account has not been activated yet.', 403)

    # Load API keys
    # If the user just deactivated a key in this session, keep current ordering
    # for this single render so the row stays in place. On subsequent visits,
    # disabled keys will be pushed to the bottom.
    keep_order_once = session.pop('keep_keys_order', None)
    if keep_order_once:
        api_keys = (
            APIKey.query
            .filter_by(user_id=authenticated_user.id)
            .order_by(APIKey.key_name)
            .all()
        )
    else:
        api_keys = (
            APIKey.query
            .filter_by(user_id=authenticated_user.id)
            .order_by(
                db.case((APIKey.state == 'enabled', 0), else_=1),
                APIKey.key_name
            )
            .all()
        )

    # Prepare data for template
    keys_data = [
        {
            'id': k.id,
            'key_name': k.key_name,
            'key_value': k.key_value,
            'state': k.state,
            'created_at': k.created_at,
            'last_used': k.last_used,
        }
        for k in api_keys
    ]

    user_data = {
        'email': authenticated_user.email,
        'user_id': authenticated_user.user_id,
    }

    return render_template('keys.html', user=user_data, api_keys=keys_data)

@main_bp.route('/deactivate-key/<int:key_id>', methods=['POST'])
def deactivate_key(key_id):
    """Deactivate an API key (server-side form processing)."""
    # Require login
    if 'user_id' not in session:
        flash('You need to be logged in to perform this action.', 'error')
        return redirect(url_for('auth.login'))

    # Look up authenticated user by public user_id stored in session
    authenticated_user = User.query.filter_by(user_id=session['user_id']).first()
    if not authenticated_user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    # Must be active account
    if not authenticated_user.is_active():
        flash('Account not activated.', 'error')
        return redirect(url_for('auth.login'))

    # Find the API key
    api_key = APIKey.query.filter_by(id=key_id, user_id=authenticated_user.id).first()
    if not api_key:
        flash('API key not found or access denied.', 'error')
        return redirect(url_for('main.user_keys', user_id=authenticated_user.user_id))

    # Deactivate the key
    if api_key.state.lower() == 'enabled':
        api_key.state = 'disabled'
        db.session.commit()
        flash(f'API key "{api_key.key_name}" has been deactivated.', 'success')
    else:
        flash(f'API key "{api_key.key_name}" is already inactive.', 'warning')

    # Ensure next render keeps the current order; subsequent visits will sort.
    session['keep_keys_order'] = True

    # Redirect back to keys page
    return redirect(url_for('main.user_keys', user_id=authenticated_user.user_id))

@main_bp.route('/logs/<user_id>')
def user_logs(user_id):
    """Display API usage logs for the authenticated user."""
    # Require login
    if 'user_id' not in session:
        return render_error_page('Authentication Required',
            'You need to be logged in to access this page.', 401)

    # Look up authenticated user by public user_id stored in session
    authenticated_user = User.query.filter_by(user_id=session['user_id']).first()
    if not authenticated_user:
        return render_error_page('User Not Found',
            'The requested user could not be found.', 404)

    # Enforce user can only view their own logs
    if authenticated_user.user_id != user_id:
        return render_error_page('Access Denied',
            'You can only view your own API logs.', 403)

    # Must be active account
    if not authenticated_user.is_active():
        return render_error_page('Account Not Activated',
            'This account has not been activated yet.', 403)

    # Prepare user data for template
    user_data = {
        'email': authenticated_user.email,
        'user_id': authenticated_user.user_id,
        'status': authenticated_user.status,
        'created_at': authenticated_user.created_at.strftime('%B %d, %Y')
    }

    # Load logs data server-side
    from ..models import ProxyLog, APIKey
    from datetime import datetime, timedelta
    
    # Get user's API keys
    user_api_keys = APIKey.query.filter_by(user_id=authenticated_user.id).all()
    api_key_values = [key.key_value for key in user_api_keys]
    
    # Get recent logs (last 30 days, limit 100)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    logs = ProxyLog.query.filter(
        ProxyLog.api_key_value.in_(api_key_values),
        ProxyLog.request_timestamp >= thirty_days_ago
    ).order_by(ProxyLog.request_timestamp.desc()).limit(100).all()
    
    # Get stats
    total_calls = ProxyLog.query.filter(ProxyLog.api_key_value.in_(api_key_values)).count()
    successful_calls = ProxyLog.query.filter(
        ProxyLog.api_key_value.in_(api_key_values),
        ProxyLog.response_status == 'key_pass'
    ).count()
    failed_calls = ProxyLog.query.filter(
        ProxyLog.api_key_value.in_(api_key_values),
        ProxyLog.response_status == 'key_error'
    ).count()
    
    # Calculate average processing time
    avg_time_logs = ProxyLog.query.filter(
        ProxyLog.api_key_value.in_(api_key_values),
        ProxyLog.processing_time_ms.isnot(None)
    ).all()
    avg_processing_time = 0
    if avg_time_logs:
        total_time = sum(log.processing_time_ms for log in avg_time_logs if log.processing_time_ms)
        avg_processing_time = round(total_time / len(avg_time_logs), 1) if avg_time_logs else 0
    
    # Prepare logs data for template
    logs_data = []
    for log in logs:
        logs_data.append({
            'id': log.id,
            'request_timestamp': log.request_timestamp,
            'api_key_value': log.api_key_value,
            'response_status': log.response_status,
            'request_body': log.request_body,
            'response_body': log.response_body,
            'processing_time_ms': log.processing_time_ms
        })
    
    # Prepare stats data
    stats_data = {
        'total_calls': total_calls,
        'successful_calls': successful_calls,
        'failed_calls': failed_calls,
        'avg_processing_time': avg_processing_time
    }
    
    # Prepare API keys data for filter dropdown
    api_keys_data = []
    for key in user_api_keys:
        api_keys_data.append({
            'key_name': key.key_name,
            'key_value': key.key_value,
            'state': key.state
        })

    return render_template('logs.html', 
                         user=user_data, 
                         logs=logs_data, 
                         stats=stats_data,
                         api_keys=api_keys_data)

@main_bp.route('/analytics/<user_id>')
def user_analytics(user_id):
    """Lightweight analytics dashboard with recent queries and cache stats."""
    # Require login
    if 'user_id' not in session:
        return render_error_page('Authentication Required',
            'You need to be logged in to access this page.', 401)

    # Look up authenticated user by public user_id stored in session
    authenticated_user = User.query.filter_by(user_id=session['user_id']).first()
    if not authenticated_user:
        return render_error_page('User Not Found',
            'The requested user could not be found.', 404)

    # Enforce user can only view their own analytics
    if authenticated_user.user_id != user_id:
        return render_error_page('Access Denied',
            'You can only view your own analytics.', 403)

    # Must be active account
    if not authenticated_user.is_active():
        return render_error_page('Account Not Activated',
            'This account has not been activated yet.', 403)

    user_data = {
        'email': authenticated_user.email,
        'user_id': authenticated_user.user_id,
    }
    # Provide user's API keys for filtering in analytics
    user_api_keys = APIKey.query.filter_by(user_id=authenticated_user.id).all()
    api_keys_data = [
        {
            'key_name': key.key_name,
            'key_value': key.key_value,
            'state': key.state
        }
        for key in user_api_keys
    ]

    return render_template('analytics.html', user=user_data, api_keys=api_keys_data)

@main_bp.route('/test/<key_value>')
def test_key(key_value):
    """Test API key page - allows users to test their API keys against the proxy endpoint."""
    # Require login
    if 'user_id' not in session:
        return render_error_page('Authentication Required',
            'You need to be logged in to access this page.', 401)

    # Look up authenticated user by public user_id stored in session
    authenticated_user = User.query.filter_by(user_id=session['user_id']).first()
    if not authenticated_user:
        return render_error_page('User Not Found',
            'The requested user could not be found.', 404)

    # Must be active account
    if not authenticated_user.is_active():
        return render_error_page('Account Not Activated',
            'This account has not been activated yet.', 403)

    # Verify that the API key belongs to the authenticated user
    api_key = APIKey.query.filter_by(
        key_value=key_value,
        user_id=authenticated_user.id
    ).first()
    
    if not api_key:
        return render_error_page('API Key Not Found',
            'The requested API key was not found or does not belong to you.', 404)

    # Get usage count for this API key
    usage_count = ProxyLog.query.filter_by(api_key_value=key_value).count()
    
    # Get recent usage stats (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_usage = ProxyLog.query.filter(
        ProxyLog.api_key_value == key_value,
        ProxyLog.request_timestamp >= thirty_days_ago
    ).count()
    
    # Get successful vs failed calls
    successful_calls = ProxyLog.query.filter(
        ProxyLog.api_key_value == key_value,
        ProxyLog.response_status == 'key_pass'
    ).count()
    
    failed_calls = ProxyLog.query.filter(
        ProxyLog.api_key_value == key_value,
        ProxyLog.response_status == 'key_error'
    ).count()

    # Prepare user data for template
    user_data = {
        'email': authenticated_user.email,
        'user_id': authenticated_user.user_id,
        'status': authenticated_user.status,
        'created_at': authenticated_user.created_at.strftime('%B %d, %Y')
    }
    
    # Prepare analytics data
    analytics_data = {
        'total_usage': usage_count,
        'recent_usage': recent_usage,
        'successful_calls': successful_calls,
        'failed_calls': failed_calls,
        'success_rate': round((successful_calls / usage_count * 100), 1) if usage_count > 0 else 0
    }

    return render_template('test_key.html', user=user_data, key_value=key_value, analytics=analytics_data)

@main_bp.route('/banned_keywords/<user_id>')
def banned_keywords(user_id):
    """Display banned keywords management page for the authenticated user."""
    # Require login
    if 'user_id' not in session:
        return render_error_page('Authentication Required',
            'You need to be logged in to access this page.', 401)

    # Look up authenticated user by public user_id stored in session
    authenticated_user = User.query.filter_by(user_id=session['user_id']).first()
    if not authenticated_user:
        return render_error_page('User Not Found',
            'The requested user could not be found.', 404)

    # Enforce user can only view their own banned keywords
    if authenticated_user.user_id != user_id:
        return render_error_page('Access Denied',
            'You can only view your own banned keywords.', 403)

    # Must be active account
    if not authenticated_user.is_active():
        return render_error_page('Account Not Activated',
            'This account has not been activated yet.', 403)

    # Prepare user data for template
    user_data = {
        'email': authenticated_user.email,
        'user_id': authenticated_user.user_id,
        'status': authenticated_user.status,
        'created_at': authenticated_user.created_at.strftime('%B %d, %Y')
    }

    # Get user's banned keywords
    banned_keywords = BannedKeyword.get_user_keywords(authenticated_user.id)
    
    # If user has no keywords, populate with defaults
    if not banned_keywords:
        BannedKeyword.populate_default_keywords(authenticated_user.id)
        banned_keywords = BannedKeyword.get_user_keywords(authenticated_user.id)
    
    # Convert keywords to text format (space-separated)
    keywords_text = ' '.join([keyword.keyword for keyword in banned_keywords])

    return render_template('banned_keywords.html', 
                         user=user_data, 
                         keywords_text=keywords_text)

@main_bp.route('/init-db')
def init_database():
    """Initialize database tables"""
    try:
        from ..models import db
        db.create_all()
        return jsonify({'message': 'Database initialized successfully!'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to initialize database: {str(e)}'}), 500
