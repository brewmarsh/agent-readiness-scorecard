import os
import json
from typing import Dict, Any

def load_config(path: str = ".") -> Dict[str, Any]:
    """Loads configuration from .agent-scorecard.json if it exists."""
    default_config = {
        "verbosity": "summary",
        "thresholds": {
            "acl_yellow": 10,
            "acl_red": 20,
            "type_safety": 90
        }
    }

    config_file = os.path.join(path, ".agent-scorecard.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                user_config = json.load(f)

                # Deep merge or just update
                if "thresholds" in user_config and isinstance(user_config["thresholds"], dict):
                    default_config["thresholds"].update(user_config["thresholds"])

                if "verbosity" in user_config:
                    default_config["verbosity"] = user_config["verbosity"]
        except Exception:
            # Fallback to defaults on parse error
            pass

    return default_config
