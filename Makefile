.PHONY: help install test test-unit test-cli test-full lint format type-check smoke demo clean build release-check

# Default target
help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Setup and installation
install:  ## Install package in development mode
	python -m pip install -U pip
	python -m pip install -r requirements.txt -r requirements-dev.txt
	python -m pip install -e .

install-pre-commit:  ## Install pre-commit hooks
	pre-commit install

# Testing targets
test-unit:  ## Run unit tests with coverage
	python -m pytest tests/unit --cov=teds_core --cov=teds --cov-branch --cov-report=term-missing --cov-fail-under=75

test-cli:  ## Run CLI tests
	python -m pytest tests/cli --cov=teds_core --cov=teds --cov-branch --cov-report=term-missing -v

test-full: test-unit test-cli  ## Run all tests

test: test-full  ## Alias for test-full

# Code quality
lint:  ## Run linting with ruff
	ruff check --fix .

format:  ## Format code with ruff
	ruff format .

type-check:  ## Run type checking with mypy
	mypy teds_core/ teds.py

# Demo and smoke tests
smoke-dev:  ## Run basic smoke test (development version)
	@echo "Testing CLI version (dev)..."
	python teds.py --version
	@echo "Testing demo verification (expect rc=1) (dev)..."
	@python teds.py verify demo/sample_tests.yaml --output-level warning > /dev/null; \
	if [ $$? -eq 1 ]; then echo "✅ Demo smoke test passed (dev)"; else echo "❌ Demo smoke test failed (dev)"; exit 1; fi

smoke:  ## Run basic smoke test (installed package)
	@echo "Testing installed package..."
	@command -v teds >/dev/null 2>&1 || { echo "❌ 'teds' command not found. Run 'make install' first."; exit 1; }
	@echo "Testing CLI version (installed)..."
	teds --version
	@echo "Testing demo verification (expect rc=1) (installed)..."
	@teds verify demo/sample_tests.yaml --output-level warning > /dev/null; \
	if [ $$? -eq 1 ]; then echo "✅ Demo smoke test passed (installed)"; else echo "❌ Demo smoke test failed (installed)"; exit 1; fi

demo: smoke  ## Run demo smoke test (alias)

# Release preparation
build:  ## Build package
	python -m build
	twine check dist/*

release-check: clean test-full smoke build  ## Full release readiness check
	@echo "🎉 Release readiness check passed!"

# Cleanup
clean:  ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info/ .coverage .pytest_cache/ __pycache__/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# CI simulation
ci-local: lint format type-check test-full smoke-dev  ## Simulate CI locally (pre-push check)
	@echo "🎉 Local CI simulation passed!"

ci-package: clean test-full build smoke  ## Full package testing (like CI package-smoke)
	@echo "🎉 Package CI simulation passed!"
