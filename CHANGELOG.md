# Changelog

All notable changes to this project will be documented in this file.

## [v0.40.0] - 2026-02-23

### Features
- **report:** Add configurable report styles (`full`, `actionable`, `collapsed`) to allow progressive disclosure of information (918c2a9).
- **cli:** Add `--limit-to` option to restrict analysis to specific files (bd6a3ae).
- **cli:** Add `--badge` option to generate an SVG scorecard badge (bd6a3ae).
- **llm:** Implement Provider-Agnostic Engine using `litellm` (cfd2efa).
- **fix:** Refactor `fix` command to use CRAFT prompts for higher quality LLM-driven remediation (866daf2).
- **economics:** Implement Dynamic Context Economics metric to track token budget across the dependency graph (bd47e60).
- **metrics:** Integrate AST-based nesting depth analyzer into scoring (b2de9f1).

### Bug Fixes
- **ci:** Resolve `create-pull-request` error in detached HEAD states (35de045).
- **windows:** Fix `UnicodeDecodeError` in reports when running on Windows (06d307f).
- **tests:** Mock `litellm` in CLI tests to ensure environment-independent verification (06d307f).
- **tests:** Fix `ImportError` in `test_dependencies.py` after module refactoring (805a332).
- **docs:** Add configuration documentation and example file (3325405).
- **security:** Complete security audit and resolve minor regressions (9f756ef).

### Refactoring
- **dependencies:** Move graph analysis functions to `analyzer.py` for better module cohesion.
- **tests:** Improve type safety and documentation in dependency tests (f74b21f).
- **workflow:** Streamline Agent Quality Gate and Scorecard Automation workflows.

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
