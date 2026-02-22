from typing import List, Dict, TypedDict


class FunctionMetric(TypedDict):
    name: str
    lineno: int
    complexity: float
    loc: int
    acl: float
    is_typed: bool


class FileAnalysisResult(TypedDict):
    file: str
    score: int
    issues: str
    loc: int
    complexity: float
    type_coverage: float
    function_metrics: List[FunctionMetric]
    tokens: int
    acl: float


class AdvisorFileResult(FileAnalysisResult):
    pass


class DepAnalysis(TypedDict):
    cycles: List[List[str]]
    god_modules: Dict[str, int]


class DirectoryStat(TypedDict):
    path: str
    file_count: int


class EnvironmentHealth(TypedDict):
    agents_md: bool
    linter_config: bool
    lock_file: bool
    pyproject_valid: bool


class DirectoryEntropy(TypedDict):
    avg_files: float
    warning: bool
    max_files: int
    crowded_dirs: List[str]


class TokenAnalysis(TypedDict):
    token_count: int
    alert: bool


class AnalysisResult(TypedDict):
    file_results: List[FileAnalysisResult]
    final_score: float
    missing_docs: List[str]
    project_issues: List[str]
    dep_analysis: DepAnalysis
    directory_stats: List[DirectoryStat]
