import os
from flask import Flask, render_template, jsonify
from flask_mail import Mail
from dotenv import load_dotenv
from models import db
from auth import auth

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
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    
    @app.route('/api/status')
    def api_status():
        return jsonify({
            'status': 'operational',
            'version': '1.0.0',
            'environment': os.getenv('FLASK_ENV', 'development')
        })
    
    def render_error_page(title, message, status_code):
        """Render a user-friendly error page with automatic redirect"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title} - TokenGuard</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .error-container {{
                    background: white;
                    padding: 40px;
                    border-radius: 15px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                    width: 90%;
                }}
                .error-icon {{
                    font-size: 64px;
                    margin-bottom: 20px;
                    color: #e74c3c;
                }}
                .error-title {{
                    color: #2c3e50;
                    font-size: 28px;
                    margin-bottom: 15px;
                    font-weight: bold;
                }}
                .error-message {{
                    color: #7f8c8d;
                    font-size: 16px;
                    margin-bottom: 30px;
                    line-height: 1.6;
                }}
                .home-button {{
                    background: #3498db;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 25px;
                    font-weight: bold;
                    display: inline-block;
                    margin-bottom: 20px;
                    transition: background 0.3s ease;
                }}
                .home-button:hover {{
                    background: #2980b9;
                }}
                .redirect-info {{
                    color: #95a5a6;
                    font-size: 14px;
                    margin-top: 20px;
                }}
                .countdown {{
                    color: #e74c3c;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-icon">⚠️</div>
                <div class="error-title">{title}</div>
                <div class="error-message">{message}</div>
                <a href="/" class="home-button">Go to Home Page</a>
                <div class="redirect-info">
                    You will be automatically redirected to the home page in 
                    <span class="countdown" id="countdown">10</span> seconds.
                </div>
            </div>
            
            <script>
                // Countdown timer
                let timeLeft = 10;
                const countdownElement = document.getElementById('countdown');
                
                const timer = setInterval(() => {{
                    timeLeft--;
                    countdownElement.textContent = timeLeft;
                    
                    if (timeLeft <= 0) {{
                        clearInterval(timer);
                        window.location.href = '/';
                    }}
                }}, 1000);
            </script>
        </body>
        </html>
        """, status_code

    @app.route('/user/<user_id>')
    def user_profile(user_id):
        """User profile route - users can only access their own profile"""
        from models import User
        from auth_utils import verify_jwt_token
        from flask import request
        
        # Get JWT token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return render_error_page('Authentication Required', 
                'You need to be logged in to access this page.', 401)
        
        token = auth_header.split(' ')[1]
        
        try:
            # Verify JWT token and get user info
            payload = verify_jwt_token(token)
            if not payload:
                return render_error_page('Invalid Token', 
                    'Your login session has expired. Please log in again.', 401)
            
            # Get the authenticated user
            authenticated_user = User.query.filter_by(id=payload.get('user_id')).first()
            if not authenticated_user:
                return render_error_page('User Not Found', 
                    'The requested user profile could not be found.', 404)
            
            if not authenticated_user.is_active():
                return render_error_page('Account Not Activated', 
                    'This account has not been activated yet.', 403)
            
            # Check if user is trying to access their own profile
            if authenticated_user.user_id != user_id:
                return render_error_page('Access Denied', 
                    'You can only view your own profile page.', 403)
            
            # Check if this is an AJAX request (for frontend JavaScript)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Return JSON response for AJAX requests
                return jsonify({
                    'success': True,
                    'user': {
                        'email': authenticated_user.email,
                        'user_id': authenticated_user.user_id,
                        'status': authenticated_user.status,
                        'created_at': authenticated_user.created_at.strftime('%B %d, %Y')
                    }
                })
            
            # Return HTML response for direct browser navigation
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>User Profile - {authenticated_user.email}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .profile {{ max-width: 600px; margin: 0 auto; }}
                    .header {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                    .info {{ background: white; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
                    .logout {{ background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="profile">
                    <div class="header">
                        <h1>Welcome, {authenticated_user.email}!</h1>
                        <a href="/auth/logout" class="logout">Logout</a>
                    </div>
                    <div class="info">
                        <h2>Your Profile</h2>
                        <p><strong>User ID:</strong> {authenticated_user.user_id}</p>
                        <p><strong>Email:</strong> {authenticated_user.email}</p>
                        <p><strong>Status:</strong> {authenticated_user.status}</p>
                        <p><strong>Member since:</strong> {authenticated_user.created_at.strftime('%B %d, %Y')}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
        except Exception as e:
            return render_error_page('Authentication Error', 
                'An error occurred while processing your request. Please try again.', 500)
    
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
