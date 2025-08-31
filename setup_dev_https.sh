#!/bin/bash

# Development HTTPS Setup Script
# This script creates self-signed SSL certificates for local development

set -e

echo "🔐 Setting up HTTPS for development environment..."

# Create SSL directory
mkdir -p ssl

# Generate self-signed certificate
echo "📜 Generating self-signed SSL certificate..."
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
    -subj "/C=US/ST=Development/L=Local/O=TokenGuard/CN=localhost"

# Set permissions
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem

echo "✅ SSL certificate generated successfully!"
echo ""
echo "🔧 To enable HTTPS in development:"
echo "1. Add to your config.env:"
echo "   HTTPS_ENABLED=True"
echo "   SSL_CONTEXT=ssl"
echo ""
echo "2. Run Flask with:"
echo "   flask run --cert=ssl/cert.pem --key=ssl/key.pem"
echo ""
echo "3. Access your app at: https://localhost:5000"
echo ""
echo "⚠️  Note: You'll see a browser warning about self-signed certificate"
echo "   This is normal for development. Click 'Advanced' -> 'Proceed'"
echo ""
echo "🚀 For production, use AWS with proper SSL certificates!"
