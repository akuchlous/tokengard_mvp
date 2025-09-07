.PHONY: help install run test clean lint format check run-dev run-test run-prod deploy-aws demo

# Default target
help:
	@echo "Available commands:"
	@echo "  install    - Install dependencies"
	@echo "  run        - Run the Flask app locally (development)"
	@echo "  run-dev    - Run in development mode"
	@echo "  run-dev-https - Run in development mode with HTTPS (optional)"
	@echo "  run-test   - Run in test mode"
	@echo "  run-prod   - Run in production mode"
	@echo "  kill       - Kill all Flask processes (used by other targets)"
	@echo "  test       - Run tests (kills Flask processes first)"
	@echo "  test-unit  - Run unit tests only (kills Flask processes first)"
	@echo "  test-e2e   - Run end-to-end tests only (kills Flask processes first)"
	@echo "  test-coverage - Run tests with coverage (kills Flask processes first)"
	@echo "  test-security - Run security tests only (kills Flask processes first)"
	@echo "  test-all   - Run all tests with coverage (kills Flask processes first)"
	@echo "  test-env   - Set up test environment"
	@echo "  demo       - Demo: opens home page and waits for 'q' to quit"
	@echo "  clean      - Clean up cache files"
	@echo "  lint       - Check code style with flake8"
	@echo "  format     - Format code with black"
	@echo "  check      - Run all checks (lint + test)"
	@echo "  deploy-aws - Deploy to AWS (S3 + CloudFront)"
	@echo "  release    - Run tests, bump version tag, and push tag"

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

# Run the Flask app locally (development mode)
run: run-dev

# Run in development mode
run-dev: kill
	@echo "Starting Flask app in DEVELOPMENT mode..."
	@sleep 1
	@echo "Using config.env for development configuration"
	@echo "Visit http://localhost:5000 in your browser"
	cp config.env .env && python app.py

# Run in development mode with HTTPS
run-dev-https: kill
	@echo "Starting Flask app in DEVELOPMENT mode with HTTPS..."
	@sleep 1
	@echo "Setting up HTTPS environment..."
	@if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then \
		echo "SSL certificates not found. Run './setup_dev_https.sh' first."; \
		exit 1; \
	fi
	@echo "Using config.dev.https.env for HTTPS development configuration"
	@echo "Visit https://localhost:5000 in your browser"
	@echo "⚠️  Accept the self-signed certificate warning in your browser"
	cp config.dev.https.env .env && python app.py

# Run in test mode
run-test: kill
	@echo "Starting Flask app in TEST mode..."
	@sleep 1
	@echo "Using config.test.env for test configuration"
	@echo "Visit http://localhost:5000 in your browser"
	cp config.test.env .env && python app.py

# Run in production mode
run-prod: kill
	@echo "Starting Flask app in PRODUCTION mode..."
	@sleep 1
	@echo "Using config.prod.env for production configuration"
	@echo "Visit http://localhost:5000 in your browser"
	cp config.prod.env .env && python app.py

# Run tests
test: kill
	@echo "Running tests..."
	@echo "Setting up test environment..."
	cp config.test.env .env
	pytest tests/ -v

# Release: run tests and tag a version automatically
release: test
	@echo "All tests passed. Creating a new version tag..."
	@LATEST_TAG=$$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0"); \
	MAJOR=$${LATEST_TAG#v}; MAJOR=$${MAJOR%%.*}; \
	MINOR=$${LATEST_TAG#v$${MAJOR}.}; MINOR=$${MINOR%%.*}; \
	PATCH=$${LATEST_TAG##*.}; \
	NEW_TAG=v$${MAJOR}.$${MINOR}.$$((PATCH+1)); \
	echo "Tagging $$NEW_TAG"; \
	git tag -a $$NEW_TAG -m "Auto release $$NEW_TAG"; \
	git push origin $$NEW_TAG

# Set up test environment
test-env:
	@echo "Setting up test environment..."
	cp config.test.env .env
	@echo "Test environment configured. Run 'make test' to run tests."

test-unit: kill
	@echo "Running unit tests..."
	pytest tests/test_auth_functions.py -v

test-e2e: kill
	@echo "Running end-to-end tests..."
	pytest tests/test_e2e.py -v

test-coverage: kill
	@echo "Running tests with coverage..."
	pytest --cov=. --cov-report=html --cov-report=term-missing

test-security: kill
	@echo "Running security tests..."
	pytest tests/test_auth_functions.py::TestSecurityFeatures -v

# Demo user registration flow
demo: kill
	@echo "🚀 Starting Demo: Open Home Page"
	@echo "================================"
	@echo "1. Killing existing Flask processes..."
	@echo "2. Starting Flask server in background..."
	@echo "3. Opening homepage with Selenium..."
	@echo ""
	@echo "Starting Flask server..."
	@cp config.env .env
	@LOG_FILE=demo_server.log; \
	( python app.py > $$LOG_FILE 2>&1 & ); \
	echo "Flask logs -> $$LOG_FILE"
	@echo "Waiting for server to start..."
	@sleep 5
	@echo "Checking server health..."
	@for i in 1 2 3 4 5; do \
		if curl -s http://localhost:5000/health > /dev/null; then \
			echo "✅ Server is ready!"; \
			break; \
		else \
			echo "   Server not ready, waiting... (attempt $$i/5)"; \
			sleep 2; \
		fi; \
	done
	@echo "Running Selenium demo (press Enter in terminal to end)..."
	@DEMO_LOG_FILE=demo_server.log python tests/scripts/demo.py
	@echo ""
	@echo "Demo completed! The Flask server is still running in the background."
	@echo "To stop the server, run 'make kill' or find and kill the Python process."
	@echo "You can continue using the application at http://localhost:5000"

test-all: kill
	@echo "Running all tests with coverage..."
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

# Kill Flask processes
kill:
	@echo "Killing all Flask processes..."
	@pkill -f "python app.py" || true
	@pkill -f "flask" || true
	@pkill -f "gunicorn" || true
	@lsof -ti:5000 | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo "Flask processes killed"

# Clean up cache files
clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

# Check code style (requires flake8)
lint:
	@echo "Checking code style..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 app.py test_app.py; \
	else \
		echo "flake8 not installed. Install with: pip install flake8"; \
	fi

# Format code (requires black)
format:
	@echo "Formatting code..."
	@if command -v black >/dev/null 2>&1; then \
		black app.py test_app.py; \
	else \
		echo "black not installed. Install with: pip install black"; \
	fi

# Run all checks
check: lint
	@echo "Running tests as part of check..."
	@make test

# Development setup
dev-setup: install
	@echo "Development environment setup complete!"
	@echo "Run 'make run' to start the app"
	@echo "Run 'make test' to run tests"

# Production-like run with gunicorn
prod-run:
	@echo "Starting Flask app with gunicorn..."
	@echo "Visit http://localhost:8000 in your browser"
	gunicorn -w 4 -b 0.0.0.0:8000 app:app

# AWS Deployment
deploy-aws:
	@echo "Deploying to AWS..."
	@echo "This will deploy the Flask app to AWS S3 + CloudFront"
	@echo "Make sure you have AWS CLI configured and proper permissions"
	@echo ""
	@echo "Step 1: Building static files..."
	@echo "Step 2: Uploading to S3..."
	@echo "Step 3: Invalidating CloudFront cache..."
	@echo ""
	@echo "For now, this is a placeholder. Run the deploy script manually:"
	@echo "  ./deploy.sh"
	@echo ""
	@echo "Or set up your AWS deployment pipeline as needed."

# AWS S3 deployment only
deploy-s3:
	@echo "Deploying to AWS S3..."
	@if [ -f "./deploy.sh" ]; then \
		./deploy.sh; \
	else \
		echo "deploy.sh not found. Please set up your deployment script first."; \
	fi

# Check AWS configuration
check-aws:
	@echo "Checking AWS configuration..."
	@if command -v aws >/dev/null 2>&1; then \
		echo "AWS CLI is installed"; \
		aws sts get-caller-identity; \
	else \
		echo "AWS CLI not installed. Install with: pip install awscli"; \
	fi
