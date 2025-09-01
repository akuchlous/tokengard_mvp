from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from models import db, User, ActivationToken, PasswordResetToken, APIKey
from auth_utils import (
    create_user, send_activation_email, authenticate_user, 
    generate_jwt_token, verify_jwt_token, send_password_reset_email,
    get_user_by_token, hash_password, verify_password
)
import re
from functools import wraps

auth = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized. Please log in.'}), 401
        return f(*args, **kwargs)
    return decorated_function

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration endpoint"""
    if request.method == 'GET':
        return render_template('auth/register.html')
    
    # Handle POST request
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    # Validation
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    password_valid, password_message = validate_password(password)
    if not password_valid:
        return jsonify({'error': password_message}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'User with this email already exists'}), 409
    
    try:
        # Create user and activation token
        user, activation_token = create_user(email, password)
        
        # Send activation email
        if send_activation_email(user, activation_token):
            return jsonify({
                'message': 'Registration successful! Please check your email to activate your account.',
                'user_id': user.user_id,
                'email': email,
                'redirect_url': f'/auth/activation-sent?email={email}'
            }), 201
        else:
            # If email fails, still create user but return warning
            return jsonify({
                'message': 'Account created but activation email failed to send. Please contact support.',
                'user_id': user.user_id,
                'email': email,
                'redirect_url': f'/auth/activation-sent?email={email}'
            }), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed. Please try again.'}), 500

@auth.route('/activation-sent')
def activation_sent():
    """Show activation email sent message"""
    email = request.args.get('email', '')
    return render_template('auth/activation_sent.html', email=email)

@auth.route('/activate/<token>')
def activate_account(token):
    """Activate user account with token"""
    # First check if token exists
    activation_token = ActivationToken.query.filter_by(token=token).first()
    
    if not activation_token:
        flash('Invalid or expired activation link.', 'error')
        return redirect(url_for('auth.login'))
    
    # Check if token is valid
    if not activation_token.is_valid():
        flash('Invalid or expired activation link.', 'error')
        return redirect(url_for('auth.login'))
    
    # Get user
    user = activation_token.user
    
    if not user:
        flash('Invalid or expired activation link.', 'error')
        return redirect(url_for('auth.login'))
    
    # Activate user
    user.status = 'active'
    
    # Mark token as used
    activation_token.mark_used()
    
    # Create default API key for the user
    from models import create_default_api_key
    create_default_api_key(user.id)
    
    db.session.commit()
    
    flash('Account activated successfully! You can now log in.', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login endpoint. Supports HTML form posts and JSON API."""
    if request.method == 'GET':
        return render_template('auth/login.html')

    # If JSON payload, keep API behavior
    if request.is_json:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
    else:
        # Handle HTML form submission
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

    if not email or not password:
        if request.is_json:
            return jsonify({'error': 'Email and password are required'}), 400
        flash('Email and password are required', 'error')
        return render_template('auth/login.html'), 400

    # Find user first to check activation status
    user = User.query.filter_by(email=email).first()
    
    if not user:
        if request.is_json:
            return jsonify({'error': 'Invalid email or password'}), 401
        flash('Invalid email or password', 'error')
        return render_template('auth/login.html'), 401
    
    if not user.is_active():
        if request.is_json:
            return jsonify({'error': 'Account not activated. Please check your email for activation link.'}), 403
        flash('Account not activated. Please check your email for activation link.', 'error')
        return render_template('auth/login.html'), 403
    
    # Verify password
    if not verify_password(password, user.password_hash):
        if request.is_json:
            return jsonify({'error': 'Invalid email or password'}), 401
        flash('Invalid email or password', 'error')
        return render_template('auth/login.html'), 401
    
    # Update last login
    user.update_last_login()
    
    # Set session for API key management
    session['user_id'] = user.user_id
    session['user_email'] = user.email
    
    # Generate JWT token for API consumers
    token = generate_jwt_token(user.id)

    # For HTML form, redirect to profile
    if not request.is_json:
        return redirect(url_for('user_profile', user_id=user.user_id))

    # For JSON API, return JSON response
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user_id': user.user_id,
        'redirect_url': f'/user/{user.user_id}'
    }), 200

@auth.route('/logout')
def logout():
    """User logout endpoint"""
    # Clear session
    session.clear()
    
    # In a real app, you might want to blacklist the JWT token
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))

# API Key Management Endpoints
@auth.route('/api/keys', methods=['GET'])
@login_required
def list_api_keys():
    """List all API keys for the authenticated user"""
    try:
        user_id = session.get('user_id')
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        api_keys = APIKey.query.filter_by(user_id=user.id).all()
        
        keys_data = []
        for key in api_keys:
            keys_data.append({
                'id': key.id,
                'key_name': key.key_name,
                'key_value': key.key_value,
                'state': key.state,
                'created_at': key.created_at.isoformat() if key.created_at else None,
                'last_used': key.last_used.isoformat() if key.last_used else None
            })
        
        return jsonify({
            'success': True,
            'data': keys_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve API keys'}), 500

@auth.route('/api/keys', methods=['POST'])
@login_required
def create_api_key():
    """Create a new API key for the authenticated user"""
    try:
        user_id = session.get('user_id')
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        key_name = data.get('key_name', '').strip()
        
        if not key_name:
            return jsonify({'error': 'Key name is required'}), 400
        
        if len(key_name) != 6:
            return jsonify({'error': 'Key name must be exactly 6 characters'}), 400
        
        # Check if key name already exists for this user
        existing_key = APIKey.query.filter_by(user_id=user.id, key_name=key_name).first()
        if existing_key:
            return jsonify({'error': 'Key name already exists'}), 409
        
        # Generate new API key
        from models import generate_api_key_value
        key_value = generate_api_key_value()
        
        api_key = APIKey(
            user_id=user.id,
            key_name=key_name,
            key_value=key_value,
            state='enabled'
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'id': api_key.id,
                'key_name': api_key.key_name,
                'key_value': api_key.key_value,
                'state': api_key.state,
                'created_at': api_key.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create API key'}), 500

@auth.route('/api/keys/<int:key_id>/toggle', methods=['POST'])
@login_required
def toggle_api_key(key_id):
    """Enable or disable an API key"""
    try:
        user_id = session.get('user_id')
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        api_key = APIKey.query.filter_by(id=key_id, user_id=user.id).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        # Toggle state
        if api_key.state == 'enabled':
            api_key.disable()
            new_state = 'disabled'
        else:
            api_key.enable()
            new_state = 'enabled'
        
        return jsonify({
            'success': True,
            'data': {
                'id': api_key.id,
                'key_name': api_key.key_name,
                'state': new_state
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to toggle API key'}), 500

@auth.route('/api/keys/<int:key_id>/refresh', methods=['POST'])
@login_required
def refresh_api_key(key_id):
    """Refresh the value of an API key"""
    try:
        user_id = session.get('user_id')
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        api_key = APIKey.query.filter_by(id=key_id, user_id=user.id).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        if not api_key.is_enabled():
            return jsonify({'error': 'Cannot refresh disabled API key'}), 400
        
        # Refresh the key value
        api_key.refresh_key_value()
        
        return jsonify({
            'success': True,
            'data': {
                'id': api_key.id,
                'key_name': api_key.key_name,
                'key_value': api_key.key_value,
                'state': api_key.state
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to refresh API key'}), 500

@auth.route('/api/keys/<int:key_id>', methods=['DELETE'])
@login_required
def delete_api_key(key_id):
    """Delete an API key"""
    try:
        user_id = session.get('user_id')
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        api_key = APIKey.query.filter_by(id=key_id, user_id=user.id).first()
        
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        # Don't allow deletion of the default test_key
        if api_key.key_name == 'test_key':
            return jsonify({'error': 'Cannot delete the default test key'}), 400
        
        db.session.delete(api_key)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'API key deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete API key'}), 500

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request endpoint"""
    if request.method == 'GET':
        return render_template('auth/forgot_password.html')
    
    # Handle POST request
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Find user
    user = User.query.filter_by(email=email).first()
    
    if user and user.is_active():
        # Create password reset token
        reset_token = PasswordResetToken(user.id)
        db.session.add(reset_token)
        db.session.commit()
        
        # Send password reset email
        if send_password_reset_email(user, reset_token):
            return jsonify({'message': 'If active user, the email will be send for passwd reset'}), 200
        else:
            return jsonify({'error': 'Failed to send password reset email. Please try again.'}), 500
    
    # Always return success to prevent email enumeration
    return jsonify({'message': 'If an account with this email exists, a password reset link has been sent.'}), 200

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Password reset endpoint"""
    if request.method == 'GET':
        return render_template('auth/reset_password.html', token=token)
    
    # Handle POST request
    data = request.get_json()
    new_password = data.get('password', '')
    
    if not new_password:
        return jsonify({'error': 'New password is required'}), 400
    
    password_valid, password_message = validate_password(new_password)
    if not password_valid:
        return jsonify({'error': password_message}), 400
    
    # Validate token and get user
    user = get_user_by_token(token, 'password_reset')
    
    if not user:
        return jsonify({'error': 'Invalid or expired reset link'}), 400
    
    try:
        # Update password
        user.password_hash = hash_password(new_password)
        
        # Mark token as used
        reset_token = PasswordResetToken.query.filter_by(token=token).first()
        if reset_token:
            reset_token.mark_used()
        
        db.session.commit()
        
        return jsonify({'message': 'Password reset successful. You can now log in with your new password.'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Password reset failed. Please try again.'}), 500


