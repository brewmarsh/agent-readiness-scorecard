import json
import os
from typing import Dict, Any, List, Tuple, Optional

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

try:
    import tomllib as toml_parser  # type: ignore
except ImportError:
    try:
        import tomli as toml_parser  # type: ignore
    except ImportError:
        toml_parser = None  # type: ignore

from .base import BaseAnalyzer
from ..types import FunctionMetric
from ..constants import DEFAULT_THRESHOLDS


class ConfigAnalyzer(BaseAnalyzer):
    """
    Config-specific implementation of the BaseAnalyzer.
    Evaluates Agent Cognitive Load (ACL) of configuration files.
    """

    def _calculate_depth(self, data: Any) -> int:
        """
        Recursively calculates the maximum nesting depth of dictionaries and lists.
        """
        if isinstance(data, dict) and data:
            return 1 + max(self._calculate_depth(v) for v in data.values())
        if isinstance(data, list) and data:
            return 1 + max(self._calculate_depth(item) for item in data)
        return 0

    @property
    def language(self) -> str:
        return "Config"

    def score_file(
        self,
        filepath: str,
        profile: Dict[str, Any],
        thresholds: Optional[Dict[str, Any]] = None,
        cumulative_tokens: int = 0,
    ) -> Tuple[int, str, int, float, float, List[FunctionMetric]]:
        """
        Calculates score based on the selected profile for configuration files.
        """
        p_thresholds = profile.get("thresholds", {})

        if thresholds is None:
            thresholds = {
                "acl_yellow": p_thresholds.get(
                    "acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"]
                ),
                "acl_red": p_thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"]),
                "token_limit": p_thresholds.get(
                    "token_limit", DEFAULT_THRESHOLDS["token_limit"]
                ),
            }

        metrics = self.get_function_stats(filepath)
        loc = self._get_loc(filepath)

        score = 100
        details = []

        if not metrics:
            # Check if it was a parsing error
            try:
                self._parse_config(filepath)
            except Exception:
                score -= 20
                details.append("Malformed Configuration File (-20)")
                return max(score, 0), ", ".join(details), loc, 0.0, 100.0, []

            return max(score, 0), ", ".join(details), loc, 0.0, 100.0, []

        acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
        acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])
        token_limit = thresholds.get("token_limit", DEFAULT_THRESHOLDS["token_limit"])

        if cumulative_tokens > token_limit:
            penalty = 15
            score -= penalty
            details.append(
                f"Cumulative Token Budget Exceeded: {cumulative_tokens:,} > {token_limit:,} (-{penalty})"
            )

        # ConfigAnalyzer treats the whole file as one "metric"
        file_metric = metrics[0]
        acl = file_metric["acl"]

        if acl > acl_red:
            penalty = 15
            score -= penalty
            details.append(f"Red ACL detected: {acl:.1f} > {acl_red} (-{penalty})")
        elif acl > acl_yellow:
            penalty = 5
            score -= penalty
            details.append(
                f"Yellow ACL detected: {acl:.1f} > {acl_yellow} (-{penalty})"
            )

        return (
            max(score, 0),
            ", ".join(details),
            loc,
            0.0,
            100.0,
            metrics,
        )

    def get_function_stats(self, filepath: str) -> List[FunctionMetric]:
        """
        Returns statistics for the configuration file.
        """
        try:
            data = self._parse_config(filepath)
        except Exception:
            return []

        loc = self._get_loc(filepath)

        # Calculate max depth from root values
        max_depth = 0
        if isinstance(data, dict):
            if data:
                max_depth = max(self._calculate_depth(v) for v in data.values())
        elif isinstance(data, list):
            if data:
                max_depth = max(self._calculate_depth(item) for item in data)

        acl = self.calculate_acl(0.0, loc, max_depth)

        return [
            {
                "name": os.path.basename(filepath),
                "lineno": 1,
                "complexity": 0.0,
                "loc": loc,
                "acl": acl,
                "is_typed": True,
                "nesting_depth": max_depth,
            }
        ]

    def _parse_config(self, filepath: str) -> Any:
        """
        Parses the config file based on its extension.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".json":
            return json.loads(content)
        elif ext in [".yaml", ".yml"]:
            if yaml:
                return yaml.safe_load(content)
            else:
                raise ImportError("PyYAML not installed")
        elif ext == ".toml":
            if toml_parser:
                return toml_parser.loads(content)
            else:
                raise ImportError("TOML parser not available")
        else:
            raise ValueError(f"Unsupported extension: {ext}")

    def _get_loc(self, filepath: str) -> int:
        """
        Returns lines of code excluding whitespace/comments.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return sum(
                    1 for line in f if line.strip() and not line.strip().startswith("#")
                )
        except Exception:
            return 0

    def calculate_acl(self, complexity: float, loc: int, depth: int) -> float:
        """
        Calculates Agent Cognitive Load (ACL) for Config files.
        Formula: (Max Depth * 2) + (LOC / 50)
        """
        return (depth * 2.0) + (loc / 50.0)
