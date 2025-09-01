"""
Error Handlers

This module contains error handling utilities and functions.
"""

from flask import render_template

def render_error_page(title, message, status_code):
    """Render a user-friendly error page with automatic redirect"""
    return render_template('error.html', title=title, message=message), status_code

def register_error_handlers(app):
    """Register error handlers with the Flask app"""
    
    @app.errorhandler(404)
    def not_found(error):
        return render_error_page('Page Not Found', 
            'The page you are looking for does not exist.', 404)
    
    @app.errorhandler(500)
    def internal_error(error):
        from ..models import db
        db.session.rollback()
        return render_error_page('Internal Server Error', 
            'Something went wrong on our end. Please try again later.', 500)
