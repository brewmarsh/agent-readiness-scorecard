# Changelog

All notable changes to this project will be documented in this file.

## [v0.91.0] - 2026-03-05

### Refactoring
- **core:** Finalize internal package rename to `agent_readiness_scorecard` and reconcile all internal imports.
- **build:** Update `pyproject.toml` to explicitly map src-layout for Hatchling to ensure clean installations and prevent redundant 'src' folders in distribution.

## [v0.80.0] - 2026-03-03

### Features
- **cli:** Advanced filtering, sorting, and limiting for `advise` command (dab7dae, 27e3c32).

### Bug Fixes
- **js:** Improved nesting depth calculation for callbacks in JavaScript analyzer (24afdcc).
- **js:** Graceful handling of tree-sitter as optional import in JavaScript (5d90bd2).
- **core:** Improved directory pruning and import parsing guards (d106db8, 1f95001).

### Chore
- **deps:** Migration to `uv` for dependency management (a1f8bf2, 815cc9f).
- **repo:** Comprehensive repository cleanup of clutter and updated `.gitignore` (6b0734e, aefbea3).
- **ci:** Major overhaul of CI/CD workflows and Quality Gates (d6f6949, 72f9b8d).
- **types:** Automated type hint improvements across the core engine (8ba56c6, 4bc8be1).

## [v0.70.0] - 2026-02-23

### Features
- **cli:** Add dynamic `--version` string to display current package version (0362def).
- **ci:** Enforce `beta` branch requirement across all workflows to ensure proper staging (d6ce6dd, 04784fb).

### Bug Fixes
- **types:** Resolve type safety and linting issues in CLI and analyzers (5599400, 985191e, 56e8613).

### Refactoring
- **core:** Improve module cohesion by refining dependencies between analyzers and metrics.

## [v0.60.0] - 2026-02-23

### Features
- **config:** Implement `ConfigAnalyzer` to support analysis of JSON, YAML, and TOML configuration files (90d2c9d, 0117f56).
- **report:** Replace empty ACL tables with cleaner success messages when no violations are found (4dd92eb, 1c9772a).
- **java:** Add `JavaAnalyzer` with tree-sitter support for Agent Cognitive Load analysis (d5065a3).
- **javascript:** Implement comprehensive JavaScript test suite and enhance nesting depth analysis (a2e0a7d).
- **javascript:** Implement graceful degradation for JavaScript analyzer when tree-sitter is unavailable (e7fa44d).
- **context:** Support flexible agent context files beyond standard `AGENTS.md` (7bc146a).

### Bug Fixes
- **lint:** Resolve multiple CI failures by applying Ruff formatting and fixing unused imports (c1a3e66, cedd059).
- **types:** Resolve all Mypy type errors across core modules and tests (36a1b36, 745845c, db93c59).
- **javascript:** Fix `JavascriptAnalyzer` language property and import issues (5ba2294, 5d220a4).

### Refactoring
- **core:** Modularize configuration analysis and streamline reporting logic.
- **tests:** Complete type annotations and docstrings across the expanded test suite.

## [v0.50.0] - 2026-02-23

### Features
- **report:** Replace empty ACL tables with success messages when targets are met.
- **multilang:** Refactor scoring logic to Strategy Pattern to support multiple languages (ca75f3c, a4d5aa2).
- **javascript:** Add support for JavaScript/TypeScript Agent Cognitive Load (ACL) analysis using tree-sitter (555ad49, a952736).
- **docker:** Add support for Dockerfile ACL analysis (bbaf69d).
- **markdown:** Add support for Markdown file analysis (b8415ab).
- **incremental:** Implement Git-Diff aware incremental analysis for faster local feedback (529986a).
- **config:** Add language-specific thresholds and grouped reporting support (6288721).

### Bug Fixes
- **ci:** Fix branch conflict and integrate mandatory linting in scorecard automation (c67f417, c5f02b1).
- **ci:** Update scorecard automation workflow to handle non-zero exit codes correctly (631354c).

### Refactoring
- **core:** Modularize analyzers into `src/agent_readiness_scorecard/analyzers/` (Python, JavaScript, Docker, Markdown).
- **core:** Move helper functions to `auditor_utils.py` to reduce `auditor.py` complexity (d680acd).
- **core:** Refactor `analyzer.py` and `dependencies.py` to improve cohesion and reduce ACL (d9d95d1, 080fefe).

## [v0.40.0] - 2026-02-23

### Features
- **report:** Add configurable report styles (`full`, `actionable`, `collapsed`) to allow progressive disclosure of information (918c2a9).
- **cli:** Add `--limit-to` option to restrict analysis to specific files (bd6a3ae).
- **cli:** Add `--badge` option to generate an SVG scorecard badge (bd6a3ae).
- **llm:** Implement Provider-Agnostic Engine using `litellm` (cfd2efa).
- **fix:** Refactor `fix` command to use CRAFT prompts for higher quality LLM-driven remediation (866daf2).
- **economics:** Implement Dynamic Context Economics metric to track token budget across the dependency graph (bd47e60).
- **metrics:** Refactor Agent Cognitive Load (ACL) scoring formula and integrate AST-based nesting depth analyzer (f3abbab, b2de9f1).

### Bug Fixes
- **ci:** Resolve `create-pull-request` error in detached HEAD states (35de045).
- **ci:** Remove obsolete prompt linting from audit workflow (b5d4acd).
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
