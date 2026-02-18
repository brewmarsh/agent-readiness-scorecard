import os
import copy
from typing import Dict, Any, TypedDict

# Handle TOML parsing for Python 3.11+ (tomllib) and older (tomli)
try:
    import tomllib  # type: ignore
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


class Config(TypedDict):
    verbosity: str
    thresholds: Dict[str, Any]


# Unified defaults from both branches
DEFAULT_CONFIG: Config = {
    "verbosity": "summary",
    "thresholds": {
        "acl_yellow": 10,  # Warning threshold
        "acl_red": 20,  # Critical failure threshold
        "complexity": 10,
        "type_safety": 90,
    },
}


def _deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge user settings into the default configuration."""
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
                # Matches the [tool.agent-scorecard] namespace
                user_config = data.get("tool", {}).get("agent-scorecard", {})
        except Exception:
            # Fallback to DEFAULT_CONFIG if file is malformed
            pass

    return _deep_merge(DEFAULT_CONFIG, user_config)  # type: ignore
