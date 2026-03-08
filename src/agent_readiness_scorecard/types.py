from typing import List, Dict, TypedDict, Optional


class FunctionMetric(TypedDict):
    """Metrics for an individual function or method."""

    name: str
    lineno: int
    complexity: float
    loc: int
    acl: float
    is_typed: bool
    nesting_depth: int


class FileAnalysisResult(TypedDict):
    """The result of analyzing a single source file."""

    file: str
    language: str
    score: int
    issues: str
    loc: int
    complexity: float
    type_coverage: float
    function_metrics: List[FunctionMetric]
    tokens: int
    # RESOLUTION: Standardized on cumulative_tokens to reflect the full dependency context budget
    cumulative_tokens: int
    acl: float


class AdvisorFileResult(FileAnalysisResult):
    """File results with additional context for the Advisor report."""

    pass


class DepAnalysis(TypedDict):
    """Analysis of project-level dependencies and entanglements."""

    cycles: List[List[str]]
    god_modules: Dict[str, int]


class DirectoryStat(TypedDict):
    """Stats for directory entropy analysis."""

    path: str
    file_count: int


class EnvironmentHealth(TypedDict):
    """Checklist for the project's agent-readiness environment."""

    agents_md: bool
    linter_config: bool
    lock_file: bool
    pyproject_valid: bool
    baml_detected: bool


class DirectoryEntropy(TypedDict):
    """Metrics for repository structure complexity."""

    avg_files: float
    warning: bool
    max_files: int
    crowded_dirs: List[str]


class TokenAnalysis(TypedDict):
    """Simple token count analysis for a specific block or file."""

    token_count: int
    alert: bool


class AnalysisResult(TypedDict):
    """The final payload containing the full project analysis."""

    file_results: List[FileAnalysisResult]
    final_score: float
    missing_docs: List[str]
    project_issues: List[str]
    dep_analysis: DepAnalysis
    directory_stats: List[DirectoryStat]
    report_style: Optional[str]
    environment_health: Optional[EnvironmentHealth]
