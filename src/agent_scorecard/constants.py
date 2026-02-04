# --- CONSTANTS ---
AGENT_CONTEXT_TEMPLATE = """# Agent Context: {project_name}

## Project Goal
[Brief description of what this project does]

## Architecture
- **Entry Point:** [Main file]
- **Key Modules:**
    - `module_a`: Handles X
    - `module_b`: Handles Y

## Developer Constraints
- Use Python 3.10+
- All functions must have docstrings
- Type hints are strict
"""

INSTRUCTIONS_TEMPLATE = """# Instructions

1. **Install Dependencies:** `pip install -r requirements.txt`
2. **Run Tests:** `pytest`
3. **Lint:** `pylint src/`
"""

TYPE_HINT_STUB = "# TODO: Add type hints for Agent clarity"
DOCSTRING_TEXT = '"""TODO: Add docstring for AI context."""'

# --- AGENT PROFILES ---
PROFILES = {
    "generic": {
        "min_type_coverage": 90,
        "required_files": ["README.md"],
        "description": "Standard Agent Readiness checks (ACL & Type Safety).",
    },
    "jules": {
        "min_type_coverage": 90,
        "required_files": ["agents.md", "instructions.md"],
        "description": "High autonomy profile with strict requirements.",
    },
    "copilot": {
        "min_type_coverage": 90,
        "required_files": [],
        "description": "Optimized for small context completion.",
    },
}
