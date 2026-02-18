import os
import sys
from typing import Dict, Any, TypedDict

try:
    import tomllib  # type: ignore
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        # Fallback for environments where neither is installed yet during initialization
        tomllib = None

class Thresholds(TypedDict):
    acl_yellow: int
    acl_red: int
    type_safety: int

class Config(TypedDict):
    verbosity: str
    thresholds: Thresholds

DEFAULT_CONFIG: Config = {
    "verbosity": "summary",
    "thresholds": {
        "acl_yellow": 10,
        "acl_red": 20,
        "type_safety": 90,
    },
}

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges two dictionaries."""
    for key, value in override.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            base[key] = deep_merge(base[key].copy(), value)
        else:
            base[key] = value
    return base

def load_config(path: str = ".") -> Config:
    """Loads configuration from pyproject.toml and merges with defaults."""
    # Start with a deep copy of the default config
    config: Config = {
        "verbosity": DEFAULT_CONFIG["verbosity"],
        "thresholds": DEFAULT_CONFIG["thresholds"].copy()
    }

    if tomllib is None:
        return config

    pyproject_path = os.path.join(path, "pyproject.toml")
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            user_config = data.get("tool", {}).get("agent-scorecard", {})
            if user_config:
                config = deep_merge(config, user_config)  # type: ignore
        except Exception:
            # Fallback if parsing fails or other issues occur
            pass

    return config
