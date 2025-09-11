.PHONY: help test test-unit test-cli test-schema test-full coverage dev-install package clean
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "TeDS Development Workflow"
	@echo "========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Testing targets
test-unit: ## Run unit tests only (fast, always required)
	pytest tests/unit --cov=teds_core --cov=teds --cov-branch --cov-report=term-missing --cov-fail-under=75 -q

test-cli: ## Run CLI integration tests
	pytest tests/cli -v

test-schema: ## Validate spec_schema.yaml against spec_schema.tests.yaml
	python -m teds_core.cli verify spec_schema.tests.yaml --output-level error

test: test-unit ## Default test target (unit tests only)

test-full: test-unit test-cli test-schema ## Run all tests (required for packaging)
	@echo "✅ All tests passed - ready for packaging"

# Coverage
coverage: ## Generate detailed coverage report
	pytest tests/unit --cov=teds_core --cov=teds --cov-branch --cov-report=html --cov-report=term-missing --cov-fail-under=75
	@echo "📊 Coverage report generated in htmlcov/"

# Development
dev-install: ## Install package in development mode
	pip install -e .
	@echo "🔧 Development installation complete - changes are immediately visible"

# Packaging
clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

package: clean test-full ## Build distribution packages (requires all tests to pass)
	hatch build
	@echo "📦 Package built successfully:"
	@ls -la dist/
	@echo ""
	@echo "Version info:"
	@python -c "from teds_core.version import get_version; print(f'Built version: {get_version()}')"

# Development version management
dev-version: ## Show current development version
	@echo "Current version: $$(python -c 'from teds_core.version import get_version; print(get_version())')"
	@echo "Latest git tag: $$(git describe --tags --abbrev=0 2>/dev/null || echo 'no tags')"
	@echo "Git status: $$(git status --porcelain | wc -l | tr -d ' ') uncommitted changes"

# Quick checks
check-version: dev-version ## Alias for dev-version

status: ## Show project status
	@echo "TeDS Project Status"
	@echo "=================="
	@make dev-version
	@echo ""
	@echo "Test status:"
	@make test-unit >/dev/null 2>&1 && echo "✅ Unit tests: PASS" || echo "❌ Unit tests: FAIL"
	@make test-schema >/dev/null 2>&1 && echo "✅ Schema validation: PASS" || echo "❌ Schema validation: FAIL"
	@echo ""
	@echo "Git branch: $$(git branch --show-current)"