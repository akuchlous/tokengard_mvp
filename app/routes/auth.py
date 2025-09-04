"""
Authentication Routes

FLOW OVERVIEW
- /auth/register [GET, POST]
  • Render form / validate + create user + send activation; redirect to activation-sent.
- /auth/activation-sent [GET]
  • Informational page after registration.
- /auth/activate/<token> [GET]
  • Validate token → activate user → provision default API keys.
- /auth/login [GET, POST]
  • Render form / authenticate → set session → redirect to profile.
- /auth/logout [GET]
  • Clear session and redirect to home.
- /auth/forgot-password [GET, POST]
  • Render form / generate reset token and send email.
- /auth/reset-password/<token> [GET, POST]
  • Render form / validate token and update password.
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session, current_app
from ..models import db, User, ActivationToken, PasswordResetToken, APIKey
from ..utils.auth_utils import (
    create_user, send_activation_email, authenticate_user, 
    generate_jwt_token, verify_jwt_token, send_password_reset_email,
    get_user_by_token, hash_password, verify_password
)
import re
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """Decorator to require user login"""
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

@auth_bp.route('/register', methods=['GET', 'POST'])
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

        # In testing environment, auto-activate the account and skip email
        app_env = current_app.config.get('ENV', 'development')
        is_testing = current_app.config.get('TESTING', False) or app_env in ['test', 'testing']
        if is_testing:
            user.status = 'active'
            if activation_token:
                activation_token.mark_used()
            # Provision default API keys for convenience in tests
            APIKey.create_default_api_keys(user.id)
            db.session.commit()
            return jsonify({
                'message': 'Registration successful (auto-activated for testing).',
                'user_id': user.user_id,
                'email': email,
                'redirect_url': url_for('auth.login')
            }), 201

        # Send activation email in non-testing environments
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

@auth_bp.route('/activation-sent')
def activation_sent():
    """Show activation email sent message"""
    email = request.args.get('email', '')
    return render_template('auth/activation_sent.html', email=email)

@auth_bp.route('/activate/<token>')
def activate_account(token):
    """Activate user account with token"""
    try:
        # Find the activation token
        activation_token = ActivationToken.query.filter_by(token=token).first()
        
        if not activation_token:
            flash('Invalid or expired activation token.', 'error')
            return redirect(url_for('auth.login'))
        
        if activation_token.used:
            flash('This activation token has already been used.', 'error')
            return redirect(url_for('auth.login'))
        
        if not activation_token.is_valid():
            flash('This activation token has expired.', 'error')
            return redirect(url_for('auth.login'))
        
        # Get the user
        user = User.query.get(activation_token.user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('auth.login'))
        
        # Activate the user
        user.status = 'active'
        activation_token.mark_used()
        
        # Create default API keys for the user
        from ..models import APIKey
        APIKey.create_default_api_keys(user.id)
        
        db.session.commit()
        
        flash('Account activated successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred during activation. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login endpoint"""
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    # Handle POST request
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    
    # Validation
    if not email or not password:
        flash('Email and password are required.', 'error')
        return render_template('auth/login.html')
    
    try:
        # Authenticate user
        user = authenticate_user(email, password)
        
        if user:
            if not user.is_active():
                flash('Account not activated. Please check your email for activation link.', 'error')
                return render_template('auth/login.html')
            
            # Set session
            session['user_id'] = user.user_id
            session['user_email'] = user.email
            
            # Update last login
            user.update_last_login()
            
            flash(f'Welcome back, {user.email}!', 'success')
            return redirect(url_for('main.user_profile', user_id=user.user_id))
        else:
            flash('Invalid email or password.', 'error')
            return render_template('auth/login.html')
            
    except Exception as e:
        flash('An error occurred during login. Please try again.', 'error')
        return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """User logout endpoint"""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password endpoint"""
    if request.method == 'GET':
        return render_template('auth/forgot_password.html')
    
    email = request.form.get('email', '').strip().lower()
    
    if not email:
        flash('Email is required.', 'error')
        return render_template('auth/forgot_password.html')
    
    try:
        user = User.query.filter_by(email=email).first()
        if user and user.is_active():
            # Create password reset token
            reset_token = PasswordResetToken(user.id)
            db.session.add(reset_token)
            db.session.commit()
            
            # Send password reset email
            if send_password_reset_email(user, reset_token):
                flash('Password reset instructions have been sent to your email.', 'success')
            else:
                flash('Failed to send password reset email. Please try again.', 'error')
        else:
            # Don't reveal if user exists or not
            flash('If an account with that email exists, password reset instructions have been sent.', 'info')
        
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred. Please try again.', 'error')
        return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token endpoint"""
    if request.method == 'GET':
        return render_template('auth/reset_password.html', token=token)
    
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not password or not confirm_password:
        flash('Password and confirmation are required.', 'error')
        return render_template('auth/reset_password.html', token=token)
    
    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return render_template('auth/reset_password.html', token=token)
    
    # Validate password strength
    password_valid, password_message = validate_password(password)
    if not password_valid:
        flash(password_message, 'error')
        return render_template('auth/reset_password.html', token=token)
    
    try:
        # Find the reset token
        reset_token = PasswordResetToken.query.filter_by(token=token).first()
        
        if not reset_token:
            flash('Invalid or expired reset token.', 'error')
            return redirect(url_for('auth.login'))
        
        if reset_token.used:
            flash('This reset token has already been used.', 'error')
            return redirect(url_for('auth.login'))
        
        if not reset_token.is_valid():
            flash('This reset token has expired.', 'error')
            return redirect(url_for('auth.login'))
        
        # Get the user
        user = User.query.get(reset_token.user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('auth.login'))
        
        # Update password
        user.password_hash = hash_password(password)
        reset_token.mark_used()
        
        db.session.commit()
        
        flash('Password has been reset successfully. You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred during password reset. Please try again.', 'error')
        return render_template('auth/reset_password.html', token=token)
