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
    
    @app.route('/user/<user_id>')
    def user_profile(user_id):
        """User profile route"""
        from models import User
        from auth_utils import hash_password
        
        # In a real app, you'd verify JWT token here
        # For now, we'll just check if user exists
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.is_active():
            return jsonify({'error': 'Account not activated'}), 403
        
        return render_template('dashboard/dashboard.html', user=user)
    
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
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
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
