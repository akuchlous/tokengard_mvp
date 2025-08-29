import bcrypt
import jwt
import secrets
import string
from datetime import datetime, timedelta
from flask import current_app, url_for
from flask_mail import Message
from models import db, User, ActivationToken, PasswordResetToken

def hash_password(password):
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def generate_jwt_token(user_id, expires_in=3600):
    """Generate a JWT token for user authentication"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

def verify_jwt_token(token):
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def create_user(email, password):
    """Create a new user with hashed password"""
    # Validate input
    if not email or not email.strip():
        raise ValueError("Email cannot be empty")
    if not password or not password.strip():
        raise ValueError("Password cannot be empty")
    
    password_hash = hash_password(password)
    user = User(email=email, password_hash=password_hash)
    
    db.session.add(user)
    db.session.flush()  # Flush to get the user.id
    
    # Create activation token
    activation_token = ActivationToken(user.id)
    
    db.session.add(activation_token)
    db.session.commit()
    
    return user, activation_token

def send_activation_email(user, activation_token):
    """Send activation email to user"""
    from flask import current_app
    from flask_mail import Message
    
    activation_url = url_for('auth.activate_account', token=activation_token.token, _external=True)
    
    msg = Message(
        'Activate Your Account - TokenGuard',
        recipients=[user.email],
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    
    msg.html = f"""
    <html>
        <body>
            <h2>Welcome to TokenGuard!</h2>
            <p>Please click the link below to activate your account:</p>
            <p><a href="{activation_url}">Activate Account</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't create this account, please ignore this email.</p>
        </body>
    </html>
    """
    
    try:
        # For testing purposes, just log the email
        current_app.logger.info(f"Would send activation email to {user.email}: {activation_url}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send activation email: {e}")
        return False

def send_password_reset_email(user, reset_token):
    """Send password reset email to user"""
    from flask import current_app
    from flask_mail import Message
    
    reset_url = url_for('auth.reset_password', token=reset_token.token, _external=True)
    
    msg = Message(
        'Password Reset Request - TokenGuard',
        recipients=[user.email],
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    
    msg.html = f"""
    <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>You requested a password reset for your TokenGuard account.</p>
            <p>Click the link below to reset your password:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this reset, please ignore this email.</p>
        </body>
    </html>
    """
    
    try:
        # For testing purposes, just log the email
        current_app.logger.info(f"Would send password reset email to {user.email}: {reset_url}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email: {e}")
        return False

def authenticate_user(email, password):
    """Authenticate user with email and password"""
    user = User.query.filter_by(email=email).first()
    
    if user and verify_password(password, user.password_hash):
        if user.is_active():
            user.update_last_login()
            return user
        else:
            return None  # User exists but not activated
    return None

def get_user_by_token(token, token_type='activation'):
    """Get user by token (activation or password reset)"""
    if token_type == 'activation':
        token_obj = ActivationToken.query.filter_by(token=token).first()
    else:  # password reset
        token_obj = PasswordResetToken.query.filter_by(token=token).first()
    
    if token_obj and token_obj.is_valid():
        return token_obj.user
    return None

def cleanup_expired_tokens():
    """Clean up expired tokens from database"""
    now = datetime.utcnow()
    
    # Clean up expired activation tokens
    expired_activation = ActivationToken.query.filter(ActivationToken.expires_at < now).all()
    for token in expired_activation:
        db.session.delete(token)
    
    # Clean up expired password reset tokens
    expired_reset = PasswordResetToken.query.filter(PasswordResetToken.expires_at < now).all()
    for token in expired_reset:
        db.session.delete(token)
    
    db.session.commit()
