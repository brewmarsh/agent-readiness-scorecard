import warnings
from typing import List
from .analyzers.python import PythonAnalyzer, NestingDepthVisitor
from .types import FunctionMetric


def calculate_max_depth(source_code: str) -> int:
    """
    Calculates the maximum nesting depth of control flow blocks in the given source code.

    .. deprecated:: 1.0
        Use :meth:`PythonAnalyzer.calculate_max_depth` instead.
    """
    warnings.warn(
        "calculate_max_depth is deprecated, use PythonAnalyzer().calculate_max_depth() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return PythonAnalyzer().calculate_max_depth(source_code)


def get_loc(filepath: str) -> int:
    """
    Returns lines of code excluding whitespace/comments roughly.

    .. deprecated:: 1.0
        Use :meth:`PythonAnalyzer._get_loc` instead.
    """
    warnings.warn(
        "get_loc is deprecated, use PythonAnalyzer()._get_loc() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return PythonAnalyzer()._get_loc(filepath)


def get_complexity_score(filepath: str) -> float:
    """
    Returns average cyclomatic complexity for all functions in a file.

    .. deprecated:: 1.0
        Use :meth:`PythonAnalyzer.get_complexity_score` instead.
    """
    warnings.warn(
        "get_complexity_score is deprecated, use PythonAnalyzer().get_complexity_score() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return PythonAnalyzer().get_complexity_score(filepath)


def check_type_hints(filepath: str) -> float:
    """
    Returns type hint coverage percentage for functions and async functions.

    .. deprecated:: 1.0
        Use :meth:`PythonAnalyzer.check_type_hints` instead.
    """
    warnings.warn(
        "check_type_hints is deprecated, use PythonAnalyzer().check_type_hints() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return PythonAnalyzer().check_type_hints(filepath)


def calculate_acl(complexity: float, loc: int, depth: int) -> float:
    """
    Calculates Agent Cognitive Load (ACL).

    .. deprecated:: 1.0
        Use :meth:`PythonAnalyzer.calculate_acl` instead.
    """
    warnings.warn(
        "calculate_acl is deprecated, use PythonAnalyzer().calculate_acl() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return PythonAnalyzer().calculate_acl(complexity, loc, depth)


def count_tokens(filepath: str) -> int:
    """
    Estimates the number of tokens in a file (approx 4 chars/token).

    .. deprecated:: 1.0
        Use :meth:`PythonAnalyzer.count_tokens` instead.
    """
    warnings.warn(
        "count_tokens is deprecated, use PythonAnalyzer().count_tokens() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return PythonAnalyzer().count_tokens(filepath)


def get_function_stats(filepath: str) -> List[FunctionMetric]:
    """
    Returns statistics for each function in the file including ACL and Type coverage.

    .. deprecated:: 1.0
        Use :meth:`PythonAnalyzer.get_function_stats` instead.
    """
    warnings.warn(
        "get_function_stats is deprecated, use PythonAnalyzer().get_function_stats() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return PythonAnalyzer().get_function_stats(filepath)
