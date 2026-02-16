import os
import copy
from typing import Dict, Any, TypedDict

try:
    import tomllib  # type: ignore
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        # Fallback if neither is available (should not happen in target environment)
        tomllib = None

class Config(TypedDict):
    verbosity: str
    thresholds: Dict[str, Any]

DEFAULT_CONFIG: Config = {
    "verbosity": "summary",
    "thresholds": {
        "acl": 15,
        "complexity": 10,
        "type_safety": 90,
    }
}

def _deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries."""
    result = copy.deepcopy(base)
    for key, value in over.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def load_config(path: str = ".") -> Config:
    """
    Loads configuration from pyproject.toml and merges it with DEFAULT_CONFIG.
    Looks for the [tool.agent-scorecard] section.
    """
    if os.path.isfile(path):
        search_dir = os.path.dirname(os.path.abspath(path))
    else:
        search_dir = path

    config_path = os.path.join(search_dir, "pyproject.toml")
    user_config = {}

    if tomllib and os.path.exists(config_path):
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
                user_config = data.get("tool", {}).get("agent-scorecard", {})
        except Exception:
            # If parsing fails, we fall back to defaults
            pass

    return _deep_merge(DEFAULT_CONFIG, user_config)  # type: ignore
