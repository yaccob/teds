# TeDS Specialized Agents

This directory contains specialized agent configurations for the TeDS (Test-Driven Schema Development) project. Each agent focuses on specific responsibilities to ensure efficient and reproducible task execution.

## Available Agents

### 🎯 Priority Agents (Use First)

#### [teds-tdd-agent](teds-tdd-agent.md)
**Purpose:** Enforce Test-Driven Development workflow

**Use when:**
- Implementing new features
- Fixing bugs
- Adding functionality to core modules

**Key responsibilities:**
- Write test first → verify failure → implement → verify pass
- Maintain ≥85% coverage (target: 93%+)
- Reference tutorial for specifications
- Prevent anti-patterns (modifying tests after implementation)

---

#### [teds-coverage-enforcer](teds-coverage-enforcer.md)
**Purpose:** Enforce test coverage requirements

**Use when:**
- Before committing code
- Reviewing coverage reports
- Identifying untested code paths

**Key responsibilities:**
- Block commits below 85% coverage
- Validate coverage exclusions are justified
- Propose tests for uncovered code
- Distinguish unit tests (coverage required) vs CLI tests (no coverage)

---

#### [teds-commit-guard](teds-commit-guard.md)
**Purpose:** Ensure commit and PR hygiene

**Use when:**
- Creating commits
- Writing PR descriptions
- Reviewing commit history

**Key responsibilities:**
- Block ALL attribution markers (Claude/Happy references)
- Enforce conventional commit format
- Prevent coverage details in PR descriptions (unless PR is about coverage)
- Focus commit messages on business value and technical changes

---

### 🚀 Release & Deployment Agents

#### [teds-release-agent](teds-release-agent.md)
**Purpose:** Manage automated releases

**Use when:**
- Preparing patch/minor/major releases
- Creating Git tags
- Building distribution packages
- Publishing to PyPI

**Key responsibilities:**
- Verify clean working directory
- Run full test suite
- Calculate correct version bump
- Create annotated Git tags
- Build distribution packages
- Provide publishing instructions

---

### 🏗️ Architecture & Design Agents

#### [teds-json-pointer-agent](teds-json-pointer-agent.md)
**Purpose:** Handle JSON-Pointer/JSON-Path normalization

**Use when:**
- Implementing pointer/path features
- Fixing pointer parsing bugs
- Refactoring pointer handling
- Adding new pointer formats

**Key responsibilities:**
- Ensure JSON-Pointer wildcard appending (`/*`)
- Implement early normalization at CLI boundary
- Maintain single unified processing pipeline
- Treat both formats as equal first-class features

---

#### [teds-tutorial-checker](teds-tutorial-checker.md)
**Purpose:** Validate tutorial-implementation consistency

**Use when:**
- Implementing features described in tutorial
- Updating documentation
- Detecting inconsistencies
- Validating CLI examples

**Key responsibilities:**
- Always read tutorial FIRST before implementation
- Validate examples work with current code
- Update tutorial when behavior changes
- Generate tutorial.html from AsciiDoc

---

#### [teds-schema-validator](teds-schema-validator.md)
**Purpose:** Meta-validation (TeDS validating its own schemas)

**Use when:**
- Modifying spec_schema.yaml
- Adding testspec features
- Refactoring schema structure
- Detecting circular dependencies

**Key responsibilities:**
- Run `make test-schema` validation
- Maintain separation of concerns between schema components
- Understand key-as-payload parsing
- Prevent circular schema references

---

## Agent Selection Guide

### For Feature Development
```
1. teds-tutorial-checker  → Read specification
2. teds-tdd-agent         → Implement with TDD
3. teds-coverage-enforcer → Verify coverage
4. teds-commit-guard      → Clean commit
```

### For JSON-Pointer/Path Work
```
1. teds-tutorial-checker     → Verify specification
2. teds-json-pointer-agent   → Implement normalization
3. teds-tdd-agent            → Test coverage
4. teds-commit-guard         → Commit
```

### For Schema Changes
```
1. teds-schema-validator  → Understand structure
2. teds-tdd-agent         → Implement changes
3. make test-schema       → Meta-validation
4. teds-tutorial-checker  → Update docs
5. teds-commit-guard      → Commit
```

### For Releases
```
1. teds-coverage-enforcer → Verify coverage
2. teds-commit-guard      → Clean history
3. teds-release-agent     → Create release
4. [Manual: git push + PyPI upload]
```

---

## Common Workflows

### Adding a New Feature

```bash
# 1. Check tutorial specification
# Use: teds-tutorial-checker

# 2. Write failing test first
# Use: teds-tdd-agent
pytest tests/unit/test_new_feature.py::test_my_feature -v  # Should FAIL

# 3. Implement feature
# Use: teds-tdd-agent
# Edit production code

# 4. Verify test passes
pytest tests/unit/test_new_feature.py::test_my_feature -v  # Should PASS

# 5. Check coverage
# Use: teds-coverage-enforcer
pytest tests/unit --cov=teds_core --cov=teds --cov-branch --cov-fail-under=85 -q

# 6. Commit with clean message
# Use: teds-commit-guard
git add .
git commit -m "feat: add new feature description"
```

### Fixing a Bug

```bash
# 1. Write test that reproduces bug
# Use: teds-tdd-agent
pytest tests/unit/test_bugfix.py -v  # Should FAIL

# 2. Fix the bug
# Use: teds-tdd-agent
# Edit production code

# 3. Verify test passes
pytest tests/unit/test_bugfix.py -v  # Should PASS

# 4. Coverage check + commit
# Use: teds-coverage-enforcer, teds-commit-guard
make test && git commit -m "fix: resolve bug description"
```

### Creating a Release

```bash
# 1. Verify everything is clean
# Use: teds-release-agent
make check-clean
make test-full

# 2. Create release
# Use: teds-release-agent
make release-patch  # or release-minor, release-major

# 3. Review and publish
git show v0.2.6
git push origin v0.2.6
twine upload dist/*
```

---

## Agent Usage Tips

### ✅ Best Practices

- **Use tutorial-checker FIRST** for any feature work
- **Never skip teds-tdd-agent** for implementation tasks
- **Always run teds-coverage-enforcer** before commits
- **Let teds-commit-guard** review all commit messages
- **Use teds-release-agent** for all releases (no manual versioning)

### ❌ Anti-patterns

- Implementing without reading tutorial first
- Skipping test-first workflow
- Committing without coverage check
- Manual version bumping
- Including attribution markers in commits
- Adding coverage stats to PR descriptions

---

## How Agents Work

### Technical Format

Agents are defined as **Markdown files with YAML frontmatter**:

```markdown
---
name: agent-name
description: When this agent should be invoked
tools: Read, Write, Edit, Bash, Grep, Glob
model: sonnet
---

Agent's system prompt and instructions...
```

**The YAML frontmatter is critical** - it makes the agent executable by Claude Code. Without it, the file is just documentation.

### Relationship to CLAUDE.md

**Agents COMPLEMENT (not replace) CLAUDE.md:**

- **CLAUDE.md** = Project handbook, constitution, "the law"
  - Defines WHAT and WHY
  - Project-wide rules and principles
  - Architectural decisions
  - Development history

- **Agents** = Execution playbooks, SOPs, "the instructions"
  - Define HOW exactly
  - Task-specific workflows
  - Step-by-step commands
  - Isolated responsibilities

**Workflow:** Claude reads CLAUDE.md for context → Uses agents for specific tasks

### Invoking Agents

Agents can be used:
1. **Explicitly** - "Use teds-tdd-agent to implement this"
2. **Automatically** - Claude delegates based on agent descriptions
3. **Chained** - One agent calls another for sub-tasks

---

## Project Context

**TeDS** is a Test-Driven Schema Development tool that validates JSON Schemas against YAML test specifications. Key principles:

- **TDD mandatory** - Test first, always
- **≥85% coverage** - Non-negotiable minimum
- **Tutorial is truth** - Authoritative specification
- **Clean commits** - No attribution markers, ever
- **Makefile workflow** - Maven/Gradle-style automation

**Current Status:**
- Branch: `master`
- Coverage: 93.0% (152 tests)
- Requirement: ≥85% coverage

**Critical Commands:**
```bash
make test          # Quick unit tests
make test-full     # All tests (required for release)
make coverage      # HTML coverage report
make test-schema   # Meta-validation
make release-patch # Create release
```

---

## Further Reading

- [CLAUDE.md](../../CLAUDE.md) - Full project instructions
- [Tutorial](../../docs/tutorial.adoc) - Feature specifications
- [Makefile](../../Makefile) - Available commands
- [pyproject.toml](../../pyproject.toml) - Project configuration
