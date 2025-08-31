#!/usr/bin/env python3
"""
Simple script to activate a user for testing purposes
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import User, db

def activate_user(email):
    """Activate a user by email"""
    app = create_app()
    
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            user.status = 'active'
            db.session.commit()
            print(f"✅ User {email} activated successfully!")
            print(f"   User ID: {user.user_id}")
            print(f"   Status: {user.status}")
        else:
            print(f"❌ User {email} not found!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python activate_user.py <email>")
        sys.exit(1)
    
    email = sys.argv[1]
    activate_user(email)
