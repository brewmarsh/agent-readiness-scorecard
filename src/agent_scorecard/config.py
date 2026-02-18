import os
import copy
from typing import Dict, Any, TypedDict, cast
from .constants import DEFAULT_THRESHOLDS

# Handle TOML parsing for Python 3.11+ (tomllib) and older (tomli)
try:
    import tomllib  # type: ignore
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        # Fallback for environments where neither is installed yet
        tomllib = None  # type: ignore


class Thresholds(TypedDict, total=False):
    acl_yellow: int
    acl_red: int
    complexity: int
    type_safety: int


class Config(TypedDict):
    verbosity: str
    thresholds: Thresholds


# Unified defaults representing core Agent Physics
DEFAULT_CONFIG: Config = {
    "verbosity": "summary",
    "thresholds": cast(Thresholds, DEFAULT_THRESHOLDS),
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge user settings into the default configuration."""
    result = copy.deepcopy(base)
    for key, value in override.items():
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
                # Parse settings from the standardized PEP 518 [tool] table
                user_config = data.get("tool", {}).get("agent-scorecard", {})
        except Exception:
            # Fallback to DEFAULT_CONFIG if file is malformed or inaccessible
            pass

    return cast(Config, _deep_merge(cast(Dict[str, Any], DEFAULT_CONFIG), user_config))
