# Makefile for MUBI Kodi Plugin Testing

.PHONY: help install test test-verbose test-coverage test-parallel lint format clean

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install test dependencies"
	@echo "  test         - Run all tests"
	@echo "  test-verbose - Run tests with verbose output"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  test-parallel - Run tests in parallel"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black and isort"
	@echo "  clean        - Clean up generated files"
	@echo "  all          - Run format, lint, and test with coverage"

# Install test dependencies
install:
	python -m pip install -r requirements-test.txt

# Run basic tests
test:
	python -m pytest tests/ -v

# Run tests with verbose output
test-verbose:
	python -m pytest tests/ -v -s

# Run tests with coverage
test-coverage:
	python -m pytest tests/ --cov=resources --cov=addon --cov-report=html --cov-report=term-missing

# Run tests in parallel
test-parallel:
	python -m pytest tests/ -n auto

# Run specific test file
test-file:
	@read -p "Enter test file name (e.g., test_film.py): " file; \
	python -m pytest tests/$$file -v

# Run specific test function
test-function:
	@read -p "Enter test function pattern: " pattern; \
	python -m pytest tests/ -k "$$pattern" -v

# Run linting
lint:
	python -m flake8 resources/ tests/ addon.py

# Format code
format:
	python -m black resources/ tests/ addon.py
	python -m isort resources/ tests/ addon.py

# Clean up generated files
clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

# Run all quality checks and tests
all: format lint test-coverage

# Quick test run for development
quick:
	python -m pytest tests/ -x --tb=short

# Test specific module
test-film:
	python -m pytest tests/test_film.py -v

test-metadata:
	python -m pytest tests/test_metadata.py -v

test-session:
	python -m pytest tests/test_session_manager.py -v

test-navigation:
	python -m pytest tests/test_navigation_handler.py -v

test-mubi:
	python -m pytest tests/test_mubi.py -v

test-migrations:
	python -m pytest tests/test_migrations.py -v

test-playback:
	python -m pytest tests/test_playback.py -v

test-addon:
	python -m pytest tests/test_addon.py -v

test-library:
	python -m pytest tests/test_library.py -v
