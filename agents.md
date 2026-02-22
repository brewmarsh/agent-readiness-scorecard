# Agent Context: agent-scorecard

## Project Goal
`agent-scorecard` is a CLI tool that analyzes Python projects to determine how "friendly" they are for AI Agents. It scores projects based on file size, complexity, type coverage, and documentation presence.

## Architecture
- **Entry Point:** `src/agent_scorecard/main.py` (CLI)
- **Key Modules:**
    - `agent_scorecard.main`: Core logic for scoring, fixing, and reporting.
    - `agent_scorecard.analyzer`: Contains the `NestingDepthVisitor` for calculating maximum nesting depth of control flow blocks.

## Metrics
- **AST Nesting Depth:** Measures the maximum depth of nested control flow blocks (`if`, `for`, `while`, `try`, `with`, `list comprehensions`, `lambdas`). This provides a more accurate measure of structural complexity than flat LOC.

## Developer Constraints
- Use Python 3.10+
- All functions must have docstrings
- Type hints are strict (aim for >80% coverage)
- Keep files small (<150 LOC)
- Bash scripts must use standard POSIX syntax (e.g., `else` instead of `else:`)
- Codebase must be strictly formatted and linted with Ruff
- Automated PRs bypass prompt physics checks to prevent logic loops
