import os
import copy
from pathlib import Path
from typing import Dict, Any, TypedDict, cast, Union
from .constants import DEFAULT_THRESHOLDS
from .types import Thresholds

# Handle TOML parsing for Python 3.11+ (tomllib) and older (tomli)
tomllib: Any = None
try:
    import tomllib as _tomllib  # type: ignore

    tomllib = _tomllib
except ImportError:
    try:
        import tomli as _tomli

        tomllib = _tomli
    except ImportError:
        # Fallback for environments where neither is installed yet
        tomllib = None


class Config(TypedDict):
    verbosity: str
    thresholds: Thresholds


# Unified defaults representing core Agent Physics
# RESOLUTION: Use the centralized DEFAULT_THRESHOLDS from .constants
# to ensure consistency across the entire package.
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


def load_config(path: Union[str, Path] = ".") -> Config:
    """
    Loads configuration from pyproject.toml and merges it with DEFAULT_CONFIG.
    Looks for the [tool.agent-scorecard] section in accordance with PEP 518.
    """
    if os.path.isfile(path):
        search_dir = os.path.dirname(os.path.abspath(str(path)))
    else:
        search_dir = str(path)

    config_path = os.path.join(search_dir, "pyproject.toml")
    user_config = {}

    if tomllib and os.path.exists(config_path):
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
                # Parse settings from the standardized [tool.agent-scorecard] table
                user_config = data.get("tool", {}).get("agent-scorecard", {})
        except Exception:
            # Fallback to DEFAULT_CONFIG if file is malformed or inaccessible
            pass

    return cast(Config, _deep_merge(cast(Dict[str, Any], DEFAULT_CONFIG), user_config))
