# Agent Scorecard Report

**Target Agent Profile:** High autonomy profile with strict requirements
**Overall Score: 90.8/100** - PASS

✅ **Status: PASSED** - This codebase is Agent-Ready.

## 🎯 Top Refactoring Targets (Agent Cognitive Load (ACL))

ACL = Complexity + (Lines of Code / 20). Target: ACL <= 10.

| Function | File | ACL | Status |
|----------|------|-----|--------|
| `check_prompts` | `src/agent_scorecard/main.py` | 16.3 | 🔴 Red |
| `apply_fixes` | `src/agent_scorecard/fix.py` | 15.9 | 🔴 Red |
| `detect_cycles` | `src/agent_scorecard/analyzer.py` | 15.2 | 🔴 Red |
| `check_critical_context_tokens` | `src/agent_scorecard/auditor.py` | 13.9 | 🟡 Yellow |
| `generate_advisor_report` | `src/agent_scorecard/report.py` | 13.3 | 🟡 Yellow |
| `score_file` | `src/agent_scorecard/scoring.py` | 12.2 | 🟡 Yellow |
| `resolve_module_path` | `src/agent_scorecard/graph.py` | 11.2 | 🟡 Yellow |
| `_extract_signature_from_node` | `src/agent_scorecard/auditor.py` | 11.1 | 🟡 Yellow |
| `score` | `src/agent_scorecard/main.py` | 10.4 | 🟡 Yellow |
| `build_dependency_graph` | `src/agent_scorecard/graph.py` | 10.3 | 🟡 Yellow |

## 🛡️ Type Safety Index

Target: >90% of functions must have explicit type signatures.

| File | Type Safety Index | Status |
| :--- | :---------------: | :----- |
| tests/test_report_full.py | 0% | ❌ |
| tests/test_analyzer_new.py | 0% | ❌ |
| tests/test_main_metrics.py | 0% | ❌ |
| tests/test_prompt_analyzer.py | 0% | ❌ |
| tests/test_analyzer_imports.py | 0% | ❌ |
| tests/test_scoring_acl.py | 0% | ❌ |
| tests/test_fix_command.py | 0% | ❌ |
| tests/test_auditor.py | 0% | ❌ |
| tests/test_graph.py | 0% | ❌ |
| tests/test_cli.py | 0% | ❌ |
| tests/test_advisor.py | 0% | ❌ |
| tests/test_config.py | 0% | ❌ |
| tests/test_verbosity.py | 0% | ❌ |
| tests/test_report.py | 0% | ❌ |
| tests/test_acl.py | 50% | ❌ |
| tests/test_main.py | 100% | ✅ |
| tests/__init__.py | 100% | ✅ |
| tests/test_regression_guard.py | 100% | ✅ |
| tests/test_async_support.py | 100% | ✅ |
| tests/test_logic.py | 100% | ✅ |
| src/agent_scorecard/report.py | 100% | ✅ |
| src/agent_scorecard/_version.py | 100% | ✅ |
| src/agent_scorecard/prompt_analyzer.py | 100% | ✅ |
| src/agent_scorecard/analyzer.py | 100% | ✅ |
| src/agent_scorecard/__init__.py | 100% | ✅ |
| src/agent_scorecard/types.py | 100% | ✅ |
| src/agent_scorecard/fix.py | 100% | ✅ |
| src/agent_scorecard/auditor.py | 100% | ✅ |
| src/agent_scorecard/metrics.py | 100% | ✅ |
| src/agent_scorecard/config.py | 100% | ✅ |
| src/agent_scorecard/constants.py | 100% | ✅ |
| src/agent_scorecard/main.py | 100% | ✅ |
| src/agent_scorecard/graph.py | 100% | ✅ |
| src/agent_scorecard/scoring.py | 100% | ✅ |

## 🤖 Agent Prompts for Remediation (CRAFT Format)

### File: `src/agent_scorecard/analyzer.py` - High Cognitive Load
> **Context**: You are a Senior Python Engineer focused on code maintainability.
> **Request**: Refactor functions in `src/agent_scorecard/analyzer.py` with Red ACL scores.
> **Actions**:
> - Target functions: `detect_cycles`.
> - Extract nested logic into smaller helper functions.
> - Ensure all units result in an ACL score < 10.
> **Frame**: Keep functions under 50 lines. Ensure all tests pass.
> **Template**: Markdown code blocks for the refactored code.

### File: `src/agent_scorecard/fix.py` - High Cognitive Load
> **Context**: You are a Senior Python Engineer focused on code maintainability.
> **Request**: Refactor functions in `src/agent_scorecard/fix.py` with Red ACL scores.
> **Actions**:
> - Target functions: `apply_fixes`.
> - Extract nested logic into smaller helper functions.
> - Ensure all units result in an ACL score < 10.
> **Frame**: Keep functions under 50 lines. Ensure all tests pass.
> **Template**: Markdown code blocks for the refactored code.

### File: `src/agent_scorecard/main.py` - High Cognitive Load
> **Context**: You are a Senior Python Engineer focused on code maintainability.
> **Request**: Refactor functions in `src/agent_scorecard/main.py` with Red ACL scores.
> **Actions**:
> - Target functions: `check_prompts`.
> - Extract nested logic into smaller helper functions.
> - Ensure all units result in an ACL score < 10.
> **Frame**: Keep functions under 50 lines. Ensure all tests pass.
> **Template**: Markdown code blocks for the refactored code.


### 📂 Full File Analysis

| File | Score | Issues |
| :--- | :---: | :--- |
| tests/test_report_full.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_analyzer_new.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_main.py | 100 ✅ |  |
| tests/test_main_metrics.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/__init__.py | 100 ✅ |  |
| tests/test_prompt_analyzer.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_analyzer_imports.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_regression_guard.py | 100 ✅ |  |
| tests/test_scoring_acl.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_fix_command.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_auditor.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_acl.py | 80 ✅ | Type Safety Index 50% < 90% (-20) |
| tests/test_graph.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_async_support.py | 100 ✅ |  |
| tests/test_logic.py | 100 ✅ |  |
| tests/test_cli.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_advisor.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_config.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_verbosity.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| tests/test_report.py | 80 ✅ | Type Safety Index 0% < 90% (-20) |
| src/agent_scorecard/report.py | 93 ✅ | Bloated File: 220 lines (-2), 1 Yellow ACL functions (-5) |
| src/agent_scorecard/_version.py | 100 ✅ |  |
| src/agent_scorecard/prompt_analyzer.py | 100 ✅ |  |
| src/agent_scorecard/analyzer.py | 82 ✅ | Bloated File: 235 lines (-3), 1 Red ACL functions (-15) |
| src/agent_scorecard/__init__.py | 100 ✅ |  |
| src/agent_scorecard/types.py | 100 ✅ |  |
| src/agent_scorecard/fix.py | 85 ✅ | 1 Red ACL functions (-15) |
| src/agent_scorecard/auditor.py | 90 ✅ | 2 Yellow ACL functions (-10) |
| src/agent_scorecard/metrics.py | 100 ✅ |  |
| src/agent_scorecard/config.py | 100 ✅ |  |
| src/agent_scorecard/constants.py | 100 ✅ |  |
| src/agent_scorecard/main.py | 75 ✅ | Bloated File: 250 lines (-5), 1 Red ACL functions (-15), 1 Yellow ACL functions (-5) |
| src/agent_scorecard/graph.py | 90 ✅ | 2 Yellow ACL functions (-10) |
| src/agent_scorecard/scoring.py | 95 ✅ | 1 Yellow ACL functions (-5) |

---
*Generated by Agent-Scorecard*