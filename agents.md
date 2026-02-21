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
