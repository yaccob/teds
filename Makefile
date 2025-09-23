.PHONY: help test test-unit test-cli test-schema test-full coverage dev-install test-package package clean check-clean release-patch release-minor release-major check-branch pr-ready create-pr pr-status merge-pr docs docs-html docs-clean
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "TeDS Development Workflow"
	@echo "========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Testing targets
test-unit: ## Run unit tests only (fast, always required)
	pytest tests/unit --cov=teds_core --cov=teds --cov-branch --cov-report=term-missing --cov-fail-under=85 -q

test-cli: ## Run CLI integration tests
	pytest tests/cli -v

test-schema: ## Validate spec_schema.yaml against spec_schema.tests.yaml
	python -m teds_core.cli verify spec_schema.tests.yaml --output-level error

test: test-unit ## Default test target (unit tests only)

test-full: test-unit test-cli test-schema ## Run all tests (required for packaging)
	@echo "✅ All tests passed - ready for packaging"

# Coverage
coverage: ## Generate detailed coverage report
	pytest tests/unit --cov=teds_core --cov=teds --cov-branch --cov-report=html --cov-report=term-missing --cov-fail-under=85
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

test-package: ## Test that package includes required files
	@echo "🧪 Testing package contents..."
	@rm -rf dist/ .pkg-test/
	@hatch build >/dev/null 2>&1
	@python -m venv .pkg-test
	@.pkg-test/bin/pip install -q dist/*.whl
	@echo "Testing installed package functionality..."
	@cd /tmp && echo 'version: "1.0.0"\ntests: {}' > test.yaml
	@cd /tmp && /Users/yaccob/repos/github.com/yaccob/contest/.pkg-test/bin/teds verify test.yaml --output-level error >/dev/null 2>&1 && echo "✅ Package test PASSED" || (echo "❌ Package test FAILED - missing files in package" && exit 1)
	@rm -rf .pkg-test/ /tmp/test.yaml

package: clean test-full test-package ## Build distribution packages (requires all tests to pass)
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

# Release Management
check-clean: ## Verify working directory is clean for release
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "❌ Working directory not clean. Commit changes first."; \
		git status --short; \
		exit 1; \
	fi
	@echo "✅ Working directory is clean"

define do_release
	@echo "🚀 Creating $(1) release..."
	@CURRENT=$$(git describe --tags --abbrev=0 2>/dev/null | sed 's/v//' || echo "0.0.0"); \
	if [ "$(1)" = "patch" ]; then NEW=$$(echo $$CURRENT | awk -F. '{print $$1"."$$2"."$$3+1}'); \
	elif [ "$(1)" = "minor" ]; then NEW=$$(echo $$CURRENT | awk -F. '{print $$1"."$$2+1".0"}'); \
	elif [ "$(1)" = "major" ]; then NEW=$$(echo $$CURRENT | awk -F. '{print $$1+1".0.0"}'); \
	fi; \
	echo "📝 Bumping version: v$$CURRENT → v$$NEW"; \
	git tag -a "v$$NEW" -m "chore(release): v$$NEW"; \
	echo "✅ Tagged v$$NEW"; \
	make package; \
	echo "📦 Built package with version $$NEW"; \
	echo ""; \
	echo "🎉 Release v$$NEW completed successfully!"; \
	echo "Next steps:"; \
	echo "  - Review: git show v$$NEW"; \
	echo "  - Publish: git push origin v$$NEW"; \
	echo "  - Upload: twine upload dist/*"
endef

release-patch: check-clean test-full ## Create patch release (0.2.5 → 0.2.6)
	$(call do_release,patch)

release-minor: check-clean test-full ## Create minor release (0.2.5 → 0.3.0)
	$(call do_release,minor)

release-major: check-clean test-full ## Create major release (0.2.5 → 1.0.0)
	$(call do_release,major)

# Git Workflow
check-branch: ## Verify we're on correct branch and up-to-date
	@git fetch upstream 2>/dev/null || echo "⚠️  Could not fetch from remote"
	@BRANCH=$$(git branch --show-current); \
	if [ "$$BRANCH" = "master" ]; then \
		echo "❌ Cannot create PR from master branch"; \
		exit 1; \
	fi; \
	echo "✅ Current branch: $$BRANCH"

pr-ready: check-clean test-full check-branch ## Verify branch is ready for PR
	@echo "✅ Branch is ready for PR creation"

create-pr: pr-ready ## Create pull request to master branch
	@echo "🚀 Creating pull request..."
	gh pr create --base master --fill

pr-status: ## Check current PR status
	gh pr status

merge-pr: ## Merge PR after all checks pass (auto-merge with squash)
	@echo "🔄 Auto-merging PR with squash..."
	gh pr merge --auto --squash

# Documentation
docs-html: ## Generate HTML documentation from AsciiDoc
	@echo "📖 Generating HTML documentation..."
	@asciidoctor docs/tutorial.adoc -o docs/tutorial.html
	@echo "🎨 Embedding custom CSS..."
	@sed -i.bak '/<style>/r docs/tutorial-style.css' docs/tutorial.html
	@rm -f docs/tutorial.html.bak
	@echo "✅ Generated: docs/tutorial.html"
	@echo "   Features: Fixed left sidebar TOC, modern styling, responsive design"

docs-clean: ## Clean generated documentation files
	@echo "🧹 Cleaning generated documentation..."
	@rm -f docs/tutorial.html
	@echo "✅ Cleaned generated documentation files"

docs: docs-html ## Generate all documentation (default: HTML with fixed TOC)
