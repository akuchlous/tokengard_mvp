"""
Main Routes

This module contains the main application routes.
"""

from flask import Blueprint, render_template, jsonify, url_for, session, flash, redirect
from datetime import datetime
from ..models import User, APIKey, ProxyLog
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

    # Load API keys for this user (using internal DB id), ordered by key name
    api_keys = APIKey.query.filter_by(user_id=authenticated_user.id).order_by(APIKey.key_name).all()

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

    return render_template('logs.html', user=user_data)

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

    # Prepare user data for template
    user_data = {
        'email': authenticated_user.email,
        'user_id': authenticated_user.user_id,
        'status': authenticated_user.status,
        'created_at': authenticated_user.created_at.strftime('%B %d, %Y')
    }

    return render_template('test_key.html', user=user_data, key_value=key_value)

@main_bp.route('/init-db')
def init_database():
    """Initialize database tables"""
    try:
        from ..models import db
        db.create_all()
        return jsonify({'message': 'Database initialized successfully!'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to initialize database: {str(e)}'}), 500
