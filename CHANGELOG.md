# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Features
- **llm:** Implement Provider-Agnostic Engine using `litellm`.
- **fix:** Enable real LLM-based code fixing with syntax validation and markdown cleaning.
- **config:** Add `llm` configuration support in `pyproject.toml`.

## [v0.3.0] - 2026-02-21

### Features
- **cli:** Add `check-prompts` command for LLM prompt linting.
- **cli:** Add `--verbosity` flag for controlling output detail.
- **config:** Support configuration via `pyproject.toml`.
- **report:** Add Average ACL and Type Safety metrics to summary.
- **ci:** Implement automated Agent Score badge updates.
- **ci:** Enforce beta-first workflow with guardrails.
- **core:** Implement docstring coverage tracking.

### Bug Fixes
- **ci:** Fix invalid Bash syntax in Scorecard Automation workflow.
- **lint:** Apply Ruff formatting and linting across the entire codebase.
- **cli:** Resolve output inconsistencies and enhance formatting.
- **lint:** Fix unused imports and formatting issues.
- **metrics:** Fix ACL threshold calculation and defaults.
- **report:** Resolve import errors in report generation.
- **security:** Address vulnerabilities identified in security audit.
- **cli:** Restore missing warning for invalid agent profile in `score` command.

### Refactoring
- **core:** Reduce ACL complexity in core modules.
- **cli:** Improve robustness and type safety of public interfaces.
- **report:** Modularize report generation logic.

### Breaking Changes
- **workflow:** Enforce beta branch as the default for development (requires PR to main).
