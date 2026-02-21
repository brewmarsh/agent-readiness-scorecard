import os
import copy
from typing import Dict, Any, TypedDict, cast as typing_cast
from .constants import DEFAULT_THRESHOLDS

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


class Thresholds(TypedDict, total=False):
    acl_yellow: int
    acl_red: int
    complexity: int
    type_safety: int


class Config(TypedDict):
    verbosity: str
    thresholds: Thresholds


# Unified defaults representing core Agent Physics
# RESOLUTION: Use the centralized DEFAULT_THRESHOLDS from .constants
# to ensure consistency across the entire package.
DEFAULT_CONFIG: Config = {
    "verbosity": "summary",
    "thresholds": typing_cast(Thresholds, DEFAULT_THRESHOLDS),
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge user settings into the default configuration.

    Args:
        base (Dict[str, Any]): The base dictionary.
        override (Dict[str, Any]): The dictionary with overriding values.

    Returns:
        Dict[str, Any]: The merged dictionary.
    """
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

    Looks for the [tool.agent-scorecard] section in accordance with PEP 518.

    Args:
        path (str): The path to the project or pyproject.toml file (default: ".").

    Returns:
        Config: The merged configuration dictionary.
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
                # Parse settings from the standardized [tool.agent-scorecard] table
                user_config = data.get("tool", {}).get("agent-scorecard", {})
        except Exception:
            # Fallback to DEFAULT_CONFIG if file is malformed or inaccessible
            pass

    return typing_cast(
        Config, _deep_merge(typing_cast(Dict[str, Any], DEFAULT_CONFIG), user_config)
    )


def cast(t: Any, v: Any) -> Any:
    """
    Helper for type hinting merged dictionaries in a dynamic context.

    Args:
        t (Any): The type to cast to (ignored at runtime).
        v (Any): The value to cast.

    Returns:
        Any: The value v.
    """
    return v
