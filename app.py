import os
import pdb
from flask import Flask, render_template, jsonify, url_for
from flask_mail import Mail
from dotenv import load_dotenv
from models import db
from auth import auth
from datetime import datetime

# Load environment variables based on FLASK_ENV
env_file = os.getenv('FLASK_ENV', 'development')
if env_file == 'testing':
    # For testing, don't load config files, use environment variables directly
    pass
elif env_file == 'production':
    load_dotenv('config.prod.env')
else:
    load_dotenv('config.env')  # Default to development

def create_app(test_config=None):
    """Application factory pattern for production deployment"""
    app = Flask(__name__)
    
    # Configuration
    if test_config:
        # Use test configuration if provided
        app.config.update(test_config)
    else:
        # Use environment-based configuration
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///:memory:')  # Use in-memory for testing
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Email configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    
    # JWT configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 604800))
    
    # Session configuration
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cookies for localhost
    
    # Initialize extensions
    db.init_app(app)
    mail = Mail(app)
    
    # Register blueprints
    app.register_blueprint(auth, url_prefix='/auth')
    
    # Routes
    @app.route('/')
    def home():
        return render_template('index.html')
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

    @app.route('/api/get-activation-link/<email>')
    def get_activation_link(email):
        """Get activation link for a given email (for demo purposes)"""
        try:
            from models import User, ActivationToken
            
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
    
    @app.route('/api/status')
    def api_status():
        return jsonify({
            'status': 'operational',
            'version': '1.0.0',
            'environment': os.getenv('FLASK_ENV', 'development')
        })
    
    @app.route('/api/session-debug')
    def session_debug():
        """Debug endpoint to check session state"""
        from flask import session, request
        from models import User, APIKey
        
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
            user = User.query.get(session['user_id'])
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
    
    def render_error_page(title, message, status_code):
        """Render a user-friendly error page with automatic redirect"""
        return render_template('error.html', title=title, message=message), status_code

    @app.route('/user/<user_id>')
    def user_profile(user_id):
        """User profile route - server-rendered only, user can only view own profile."""
        from models import User
        from flask import session

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

    @app.route('/keys/<user_id>')
    def user_keys(user_id):
        """Display all API keys for the authenticated user (server-rendered)."""
        from models import User, APIKey
        from flask import session

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

        # Load API keys for this user (using internal DB id)
        api_keys = APIKey.query.filter_by(user_id=authenticated_user.id).order_by(APIKey.created_at.desc()).all()

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
    
    @app.route('/init-db')
    def init_database():
        """Initialize database tables"""
        try:
            db.create_all()
            return jsonify({'message': 'Database initialized successfully!'}), 200
        except Exception as e:
            return jsonify({'error': f'Failed to initialize database: {str(e)}'}), 500
    

    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_error_page('Page Not Found', 
            'The page you are looking for does not exist.', 404)
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_error_page('Internal Server Error', 
            'Something went wrong on our end. Please try again later.', 500)
    
    return app

# Create app instance
if os.getenv('FLASK_ENV') == 'testing':
    # Use test configuration for testing environment
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', 'sqlite:///:memory:'),
        'SECRET_KEY': os.getenv('SECRET_KEY', 'test-secret-key'),
        'JWT_SECRET_KEY': os.getenv('JWT_SECRET_KEY', 'test-jwt-secret-key'),
        'MAIL_SERVER': os.getenv('MAIL_SERVER', 'localhost'),
        'MAIL_PORT': int(os.getenv('MAIL_PORT', 587)),
        'MAIL_USE_TLS': os.getenv('MAIL_USE_TLS', 'False').lower() == 'true',
        'MAIL_USE_SSL': os.getenv('MAIL_USE_SSL', 'False').lower() == 'true',
        'MAIL_USERNAME': os.getenv('MAIL_USERNAME', 'test@example.com'),
        'MAIL_PASSWORD': os.getenv('MAIL_PASSWORD', 'test-password'),
        'MAIL_DEFAULT_SENDER': os.getenv('MAIL_DEFAULT_SENDER', 'test@example.com'),
        'WTF_CSRF_ENABLED': False
    }
    app = create_app(test_config)
else:
    app = create_app()

# Database initialization - will be done on first request
print("🚀 Starting TokenGuard server...")
if os.getenv('FLASK_ENV') == 'testing':
    print("🧪 Running in TESTING mode with in-memory database")
    with app.app_context():
        db.create_all()
        print("📊 Test database initialized")
elif os.getenv('DATABASE_URL') == 'sqlite:///:memory:':
    print("💾 Running with in-memory database")
    with app.app_context():
        db.create_all()
        print("📊 In-memory database initialized")
else:
    print("📊 Database will be initialized on first request")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
