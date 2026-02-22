# Agent Context: agent-scorecard

## Project Goal
`agent-scorecard` is a CLI tool that analyzes Python projects to determine how "friendly" they are for AI Agents. It scores projects based on file size, complexity, type coverage, and documentation presence.

## Architecture
- **Entry Point:** `src/agent_scorecard/main.py` (CLI)
- **Key Modules:**
    - `agent_scorecard.main`: Core logic for scoring, fixing, and reporting.

## Developer Constraints
- Use Python 3.10+
- All functions must have docstrings
- Type hints are strict (aim for >80% coverage)
- Keep files small (<150 LOC)
- Bash scripts must use standard POSIX syntax (e.g., `else` instead of `else:`)
- Codebase must be strictly formatted and linted with Ruff
- Automated PRs bypass prompt physics checks to prevent logic loops
- Documentation files must follow the uppercase naming convention (e.g., `AGENTS.md`)

## Operational Requirements
- **Fault-Tolerant Automation:** GitHub Actions workflows must handle transient states gracefully. Specifically, the 'Prompt Physics' workflow is designed to ignore 404 errors when removing labels to prevent unnecessary pipeline failures if a label has already been removed or is missing.
