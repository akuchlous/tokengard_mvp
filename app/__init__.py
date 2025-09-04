"""
TokenGuard Application Package

FLOW OVERVIEW
- create_app(test_config=None)
  • Build Flask app, apply config (test or env-based), init extensions (DB, Mail).
  • Register blueprints: auth (/auth), main (/), api (/api).
  • Register global error handlers.
"""

from flask import Flask
from flask_mail import Mail
from .models import db
from .routes import auth_bp, main_bp, api_bp
from .config import Config

def create_app(test_config=None):
    """Application factory pattern for production deployment"""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Configuration
    if test_config:
        # Use test configuration if provided
        app.config.update(test_config)
    else:
        # Use environment-based configuration
        app.config.from_object(Config())
    
    # Initialize extensions
    db.init_app(app)
    mail = Mail(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register error handlers
    from .utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    return app
