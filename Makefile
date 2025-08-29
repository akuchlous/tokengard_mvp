.PHONY: help install run test clean lint format check

# Default target
help:
	@echo "Available commands:"
	@echo "  install    - Install dependencies"
	@echo "  run        - Run the Flask app locally"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean up cache files"
	@echo "  lint       - Check code style with flake8"
	@echo "  format     - Format code with black"
	@echo "  check      - Run all checks (lint + test)"

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

# Run the Flask app locally
run:
	@echo "Starting Flask app..."
	@echo "Visit http://localhost:5000 in your browser"
	python app.py

# Run tests
test:
	@echo "Running tests..."
	pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	pytest tests/test_auth_functions.py -v -m "unit"

test-e2e:
	@echo "Running end-to-end tests..."
	pytest tests/test_e2e.py -v -m "e2e"

test-coverage:
	@echo "Running tests with coverage..."
	pytest --cov=. --cov-report=html --cov-report=term-missing

test-security:
	@echo "Running security tests..."
	pytest tests/test_auth_functions.py::TestSecurityFeatures -v

test-all:
	@echo "Running all tests with coverage..."
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

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
check: lint test

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
