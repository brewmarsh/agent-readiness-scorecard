from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
from ..types import FunctionMetric


class BaseAnalyzer(ABC):
    """
    Abstract base class for language-specific analyzers.
    """

    @property
    @abstractmethod
    def language(self) -> str:
        """
        Returns the name of the language this analyzer handles.
        """
        pass

    @abstractmethod
    def score_file(
        self,
        filepath: str,
        profile: Dict[str, Any],
        thresholds: Optional[Dict[str, Any]] = None,
        cumulative_tokens: int = 0,
    ) -> Tuple[int, str, int, float, float, List[FunctionMetric]]:
        """
        Calculates score based on the selected profile and Agent Readiness spec.

        Args:
            filepath (str): Path to the file.
            profile (Dict[str, Any]): The agent profile being used.
            thresholds (Optional[Dict[str, Any]]): Optional overrides for scoring thresholds.
            cumulative_tokens (int): Transitive token count of file and local imports.

        Returns:
            Tuple[int, str, int, float, float, List[FunctionMetric]]: Scoring results.
        """
        pass

    @abstractmethod
    def get_function_stats(self, filepath: str) -> List[FunctionMetric]:
        """
        Returns statistics for each function in the file.

        Args:
            filepath (str): Path to the file.

        Returns:
            List[FunctionMetric]: List of function-level metrics.
        """
        pass

    @abstractmethod
    def calculate_acl(self, complexity: float, loc: int, depth: int) -> float:
        """
        Calculates Agent Cognitive Load (ACL).

        Args:
            complexity (float): Cyclomatic complexity.
            loc (int): Lines of code.
            depth (int): Maximum nesting depth.

        Returns:
            float: Calculated ACL score.
        """
        pass
