from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from models import db, User, ActivationToken, PasswordResetToken
from auth_utils import (
    create_user, send_activation_email, authenticate_user, 
    generate_jwt_token, verify_jwt_token, send_password_reset_email,
    get_user_by_token, hash_password, verify_password
)
import re

auth = Blueprint('auth', __name__)

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
                'user_id': user.user_id
            }), 201
        else:
            # If email fails, still create user but return warning
            return jsonify({
                'message': 'Account created but activation email failed to send. Please contact support.',
                'user_id': user.user_id
            }), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed. Please try again.'}), 500

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
    
    db.session.commit()
    
    flash('Account activated successfully! You can now log in.', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login endpoint"""
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    # Handle POST request
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Find user first to check activation status
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not user.is_active():
        return jsonify({'error': 'Account not activated. Please check your email for activation link.'}), 403
    
    # Verify password
    if not verify_password(password, user.password_hash):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Update last login
    user.update_last_login()
    
    # Generate JWT token
    token = generate_jwt_token(user.id)
    
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
    
    if user:
        # Create password reset token
        reset_token = PasswordResetToken(user.id)
        db.session.add(reset_token)
        db.session.commit()
        
        # Send password reset email
        if send_password_reset_email(user, reset_token):
            return jsonify({'message': 'Password reset email sent. Please check your inbox.'}), 200
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


