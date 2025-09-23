#!/usr/bin/env bash
# Hook Protection Installation Script
# Run this script to install enhanced git hooks with bypass protection

set -e

echo "🛡️ Installing Git Hook Bypass Protection..."

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Install protected pre-commit hook
if [ -f ".git/hooks/pre-commit" ]; then
    echo "📄 Backing up existing pre-commit hook to pre-commit.backup"
    cp .git/hooks/pre-commit .git/hooks/pre-commit.backup
fi

echo "📝 Installing protected pre-commit hook..."
cp hooks/pre-commit-protected .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Install protected commit-msg hook
if [ -f ".git/hooks/commit-msg" ]; then
    echo "📄 Backing up existing commit-msg hook to commit-msg.backup"
    cp .git/hooks/commit-msg .git/hooks/commit-msg.backup
fi

echo "📝 Installing protected commit-msg hook..."
cp hooks/commit-msg-protected .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg

# Make safe commit script executable
echo "🔧 Setting up safe commit script..."
chmod +x .git-safe-commit.sh

# Set up git aliases for protected commits
echo "🔗 Setting up git aliases..."
git config --local alias.safe-commit '!bash ./.git-safe-commit.sh'

echo ""
echo "✅ Hook bypass protection installed successfully!"
echo ""
echo "🛡️ Protection features:"
echo "   • Blocks PRE_COMMIT_ALLOW_NO_CONFIG environment variable"
echo "   • Blocks SKIP environment variable"
echo "   • Validates virtual environment"
echo "   • Provides safe commit alternatives"
echo ""
echo "💡 Recommended workflow:"
echo "   • Use: git safe-commit -m 'message'"
echo "   • Or: git add <files> && git commit -m 'message'"
echo ""
echo "⚠️  If hooks are bypassed with --no-verify:"
echo "   • Get explicit approval first"
echo "   • Document the reason clearly"
echo "   • Fix underlying issues afterward"
