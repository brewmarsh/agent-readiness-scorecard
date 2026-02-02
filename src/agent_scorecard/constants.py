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
        "max_loc": 200,
        "max_complexity": 10,
        "min_type_coverage": 50,
        "required_files": ["README.md"],
        "description": "Standard cleanliness checks."
    },
    "jules": {
        "max_loc": 150,  # Stricter LOC for autonomy
        "max_complexity": 8,
        "min_type_coverage": 80,  # High typing requirement
        "required_files": ["agents.md", "instructions.md"],
        "description": "Strict typing and autonomy instructions."
    },
    "copilot": {
        "max_loc": 100,  # Very small chunks preferred
        "max_complexity": 15, # Lenient on logic, strict on size
        "min_type_coverage": 40,
        "required_files": [],
        "description": "Optimized for small context completion."
    }
}
