"""
Database Configuration

FLOW OVERVIEW
- Provides the global SQLAlchemy instance `db` used across all models.
- Initialized in app factory (app/__init__.py) with app context.
"""

from flask_sqlalchemy import SQLAlchemy

# Create SQLAlchemy instance
db = SQLAlchemy()
