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
        resolved_thresholds = self._resolve_thresholds(profile, thresholds)
        metrics = self.get_function_stats(filepath)
        loc = self._get_loc(filepath)

        if not metrics:
            return self._handle_malformed_config(filepath, loc)

        score, details = self._calculate_penalties(
            metrics, resolved_thresholds, cumulative_tokens
        )

        return (
            max(score, 0),
            ", ".join(details),
            loc,
            0.0,
            100.0,
            metrics,
        )

    def _resolve_thresholds(
        self, profile: Dict[str, Any], thresholds: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Resolves analysis thresholds from profile and defaults."""
        p_thresholds = profile.get("thresholds", {})
        if thresholds is None:
            return {
                "acl_yellow": p_thresholds.get(
                    "acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"]
                ),
                "acl_red": p_thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"]),
                "token_limit": p_thresholds.get(
                    "token_limit", DEFAULT_THRESHOLDS["token_limit"]
                ),
            }
        return thresholds

    def _calculate_penalties(
        self,
        metrics: List[FunctionMetric],
        thresholds: Dict[str, Any],
        cumulative_tokens: int,
    ) -> Tuple[int, List[str]]:
        """Calculates score penalties based on metrics and tokens."""
        score = 100
        details = []

        token_limit = thresholds.get("token_limit", DEFAULT_THRESHOLDS["token_limit"])
        if cumulative_tokens > token_limit:
            penalty = 15
            score -= penalty
            details.append(
                f"Cumulative Token Budget Exceeded: {cumulative_tokens:,} > {token_limit:,} (-{penalty})"
            )

        if not metrics:
            return score, details

        acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
        acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])
        acl = metrics[0]["acl"]

        if acl > acl_red:
            score -= 15
            details.append(f"Red ACL detected: {acl:.1f} > {acl_red} (-15)")
        elif acl > acl_yellow:
            score -= 5
            details.append(f"Yellow ACL detected: {acl:.1f} > {acl_yellow} (-5)")

        return score, details

    def _handle_malformed_config(
        self, filepath: str, loc: int
    ) -> Tuple[int, str, int, float, float, List[FunctionMetric]]:
        """Handles cases where the config file is malformed or cannot be parsed."""
        try:
            self._parse_config(filepath)
            return 100, "", loc, 0.0, 100.0, []
        except Exception:
            return 80, "Malformed Configuration File (-20)", loc, 0.0, 100.0, []

    def get_function_stats(self, filepath: str) -> List[FunctionMetric]:
        """
        Returns statistics for the configuration file.
        """
        try:
            data = self._parse_config(filepath)
        except Exception:
            return []

        loc = self._get_loc(filepath)
        max_depth = self._get_max_depth(data)
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

    def _get_max_depth(self, data: Any) -> int:
        """Calculates the maximum nesting depth from the root of the data."""
        if isinstance(data, dict) and data:
            return max(self._calculate_depth(v) for v in data.values())
        if isinstance(data, list) and data:
            return max(self._calculate_depth(item) for item in data)
        return 0

    def _parse_config(self, filepath: str) -> Any:
        """
        Parses the config file based on its extension.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".json":
            return json.loads(content)
        if ext in [".yaml", ".yml"]:
            return self._parse_yaml(content)
        if ext == ".toml":
            return self._parse_toml(content)

        raise ValueError(f"Unsupported extension: {ext}")

    def _parse_yaml(self, content: str) -> Any:
        """Parses YAML content if PyYAML is installed."""
        if not yaml:
            raise ImportError("PyYAML not installed")
        return yaml.safe_load(content)

    def _parse_toml(self, content: str) -> Any:
        """Parses TOML content if a parser is available."""
        if not toml_parser:
            raise ImportError("TOML parser not available")
        return toml_parser.loads(content)

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
