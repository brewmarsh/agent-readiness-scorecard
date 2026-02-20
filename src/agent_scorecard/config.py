import os
import copy
from typing import Dict, Any, TypedDict, cast as typing_cast
from .constants import DEFAULT_VERBOSITY, DEFAULT_THRESHOLDS

# Handle TOML parsing for Python 3.11+ (tomllib) and older (tomli)
try:
    import tomllib  # type: ignore
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None


class Thresholds(TypedDict, total=False):
    acl_yellow: int
    acl_red: int
    complexity: int
    type_safety: int


class Config(TypedDict):
    verbosity: str
    thresholds: Thresholds


DEFAULT_CONFIG: Config = {
    "verbosity": DEFAULT_VERBOSITY,
    "thresholds": typing_cast(Thresholds, DEFAULT_THRESHOLDS),
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
    user_config: Dict[str, Any] = {}

    if tomllib and os.path.exists(config_path):
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
                user_config = data.get("tool", {}).get("agent-scorecard", {})
        except Exception:
            # Fallback to defaults if file is malformed
            pass

    return typing_cast(
        Config, _deep_merge(typing_cast(Dict[str, Any], DEFAULT_CONFIG), user_config)
    )
