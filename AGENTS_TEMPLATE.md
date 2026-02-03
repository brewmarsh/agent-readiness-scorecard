# Agent Context: [Project Name]

> **System Instruction:** This file is the primary source of truth for all autonomous agents (Jules, Copilot, etc.) working in this repository. Read this before planning any changes.

## 1. Project Goal
[Briefly describe what this software does. E.g., "A CLI tool that evaluates Python codebases for AI-Agent readiness."]

## 2. Operational Commands (Required)
*Agents must use these exact commands to validate their work.*

| Action | Command | Expected Output |
| :--- | :--- | :--- |
| **Build** | `pip install .` | Exit code 0 |
| **Test** | `pytest tests/` | "Passed" string in stdout |
| **Style** | `ruff check .` | No errors found |
| **Run** | `agent-score --help` | Help menu display |

## 3. Architecture & Map
* **Entry Point:** `src/agent_scorecard/main.py`
* **Key Modules:**
    * `analyzer.py`: Calculates ACL and complexity metrics.
    * `graph.py`: Handles dependency graph generation (NetworkX).
    * `report.py`: Generates RECOMMENDATIONS.md.
* **Data Flow:** `CLI Input -> Graph Construction -> Metric Calculation -> Report Generation`

## 4. Development Standards
1.  **Type Hints:** All function signatures MUST have PEP 484 type hints.
    * *Good:* `def calculate(x: int) -> int:`
    * *Bad:* `def calculate(x):`
2.  **Docstrings:** Every public module and function requires a docstring describing parameters and return values.
3.  **Complexity:** Keep Cyclomatic Complexity under 10. Refactor if higher.
4.  **No Hallucinations:** Do not import libraries that are not listed in `pyproject.toml`.

## 5. Critical Constraints
* **Python Version:** >= 3.10
* **External APIs:** None (Offline tool)
* **Visualization:** Use standard libraries or `rich` for terminal output.
