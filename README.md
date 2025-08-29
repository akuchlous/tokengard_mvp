# Flask AWS App

A simple Flask application ready for deployment to AWS with a custom domain.

## Features

- 🚀 Modern, responsive landing page
- ✅ Comprehensive test suite
- 🛠️ Makefile for easy development workflow
- 📱 Mobile-friendly design
- 🔍 Health check endpoint
- 🎨 Beautiful gradient design

## Quick Start

### 1. Setup Development Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# On Windows: venv\Scripts\activate

# Install dependencies
make install
```

### 2. Run the Application

```bash
# Start Flask app locally
make run

# Visit http://localhost:5000 in your browser
```

### 3. Run Tests

```bash
# Run all tests
make test

# Run all checks (lint + test)
make check
```

## Available Make Commands

- `make help` - Show all available commands
- `make install` - Install dependencies
- `make run` - Run Flask app locally
- `make test` - Run tests
- `make clean` - Clean up cache files
- `make lint` - Check code style
- `make format` - Format code
- `make check` - Run all checks
- `make prod-run` - Run with gunicorn (production-like)

## Project Structure

```
flask-aws-app/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Makefile           # Development commands
├── test_app.py        # Test suite
├── templates/          # HTML templates
│   └── index.html     # Landing page
└── static/            # Static assets
    └── css/
        └── style.css  # Stylesheets
```

## Testing

The app includes comprehensive tests covering:
- Home page loading
- Health endpoint
- Content validation
- Error handling
- HTML structure

Run tests with: `make test`

## Next Steps: AWS Deployment

This app is ready for AWS deployment with:
1. S3 bucket for static hosting
2. CloudFront for CDN
3. Route 53 for custom domain
4. SSL certificate

## Development Workflow

1. **Local Development**: `make run` → test at localhost:5000
2. **Testing**: `make test` → verify functionality
3. **Code Quality**: `make check` → lint + test
4. **Deploy**: Ready for AWS deployment

## Requirements

- Python 3.8+
- Flask 3.0.0
- pytest for testing
- gunicorn for production
