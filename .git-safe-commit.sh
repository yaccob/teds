#!/usr/bin/env bash
# Safe Git Commit Wrapper
# Prevents accidental bypass of pre-commit hooks

set -e

# 🚫 BYPASS DETECTION
if echo "$*" | grep -qE "(--no-verify|--no-hooks)"; then
    echo "🚫 ERROR: Hook bypass detected in arguments: $*"
    echo "💡 This wrapper prevents bypassing pre-commit hooks"
    echo "🛡️  If absolutely necessary, use 'git' directly with explicit approval"
    exit 1
fi

# Check for bypass environment variables
if [ -n "$PRE_COMMIT_ALLOW_NO_CONFIG" ]; then
    echo "🚫 ERROR: PRE_COMMIT_ALLOW_NO_CONFIG detected!"
    echo "💡 Unset this variable and fix code quality issues properly"
    exit 1
fi

if [ -n "$SKIP" ] && [ "$SKIP" != "" ]; then
    echo "🚫 ERROR: SKIP environment variable detected: $SKIP"
    echo "💡 This would bypass important quality checks"
    exit 1
fi

# 🛡️ SAFETY CHECKS
if [ ! -f ".pre-commit-config.yaml" ]; then
    echo "⚠️  WARNING: No .pre-commit-config.yaml found"
    echo "💡 Consider setting up pre-commit hooks for this repository"
fi

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ] && [ -d ".venv" ]; then
    echo "⚠️  WARNING: Virtual environment not active but .venv exists"
    echo "💡 Consider running: source .venv/bin/activate"
fi

echo "🛡️ Safe commit: Running git commit with hook protection..."

# Execute the actual git commit
exec git commit "$@"
