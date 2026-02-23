.PHONY: install lint format type-check test audit lint-prompts security-scan clean

install:
	uv sync --all-extras

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

type-check:
	uv run mypy src
	uv run mypy tests

test:
	uv run pytest

# Unified audit gate for security and agent-readiness
audit: security-scan
	@echo "✅ Audit complete. Code is safe to push."

security-scan:
	@echo "🔍 Running Bandit (SAST)..."
	uv run bandit -r src/ -ll
	@echo "🔍 Running pip-audit..."
	uv run pip-audit

run-scorecard:
	@uv run agent-score score . --report .scorecard.md.tmp --verbosity quiet > /dev/null
	@cat .scorecard.md.tmp
	@rm .scorecard.md.tmp

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +