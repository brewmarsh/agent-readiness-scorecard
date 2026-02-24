import os
from typing import List, Dict, Any, Tuple, Set, Optional, cast
from .constants import PROFILES
from .analyzers.base import BaseAnalyzer
from .analyzers.python import PythonAnalyzer
from .analyzers.markdown import MarkdownAnalyzer
from .analyzers.docker import DockerAnalyzer
from .analyzers.javascript import JavascriptAnalyzer
from .analyzers.config import ConfigAnalyzer
from . import auditor
from . import dependencies
from .auditor_utils import _find_agent_context_file
from .types import FileAnalysisResult, AnalysisResult

# Re-export metrics for backward compatibility
from .metrics import (  # noqa: F401
    calculate_acl,
    get_loc,
    get_complexity_score,
    get_function_stats,
    check_type_hints,
    count_tokens,
    NestingDepthVisitor,
    calculate_max_depth,
)


# --- METRICS & GRAPH ANALYSIS ---


def get_analyzer(filepath: str) -> BaseAnalyzer:
    """
    Returns the appropriate analyzer based on file extension.

    Args:
        filepath (str): Path to the file.

    Returns:
        BaseAnalyzer: An instance of a language-specific analyzer.
    """
    if filepath.endswith(".py"):
        return PythonAnalyzer()
    if filepath.endswith(".md"):
        return MarkdownAnalyzer()

    filename = os.path.basename(filepath)
    if filename == "Dockerfile" or filename.startswith("Dockerfile."):
        return DockerAnalyzer()

    if (
        filepath.endswith(".js")
        or filepath.endswith(".jsx")
        or filepath.endswith(".ts")
        or filepath.endswith(".tsx")
    ):
        return JavascriptAnalyzer()

    if (
        filepath.endswith(".json")
        or filepath.endswith(".yaml")
        or filepath.endswith(".yml")
        or filepath.endswith(".toml")
    ):
        return ConfigAnalyzer()

    raise ValueError(f"Unsupported file type: {filepath}")


def scan_project_docs(root_path: str, required_files: List[str]) -> List[str]:
    """
    Checks for existence of agent-critical markdown files.

    Supports flexible agent context files (agents.md, .cursorrules, etc.).

    Args:
        root_path (str): The root path of the project.
        required_files (List[str]): List of filenames required for the agent.

    Returns:
        List[str]: List of missing required files.
    """
    missing = []
    if not os.path.isdir(root_path):
        return required_files

    root_files = os.listdir(root_path)
    root_files_lower = [f.lower() for f in root_files]

    for req in required_files:
        if req.lower() == "agents.md":
            # Flexible check for any valid agent context file
            if not _find_agent_context_file(root_files):
                missing.append(req)
        elif req.lower() not in root_files_lower:
            missing.append(req)
    return missing


def get_import_graph(root_path: str) -> Tuple[Dict[str, Set[str]], Dict[str, int]]:
    """
    Builds a dependency graph and calculates individual token counts.
    """
    graph = dependencies.get_import_graph(root_path)
    token_counts: Dict[str, int] = {}

    base_dir = (
        os.path.dirname(root_path)
        if os.path.isfile(root_path) and root_path.endswith(".py")
        else root_path
    )

    for rel_path in graph:
        full_path = os.path.join(base_dir, rel_path)
        token_counts[rel_path] = auditor.count_python_tokens(full_path)

    return graph, token_counts


def get_project_issues(
    path: str, py_files: List[str], profile: Dict[str, Any]
) -> Tuple[int, List[str]]:
    """
    Analyzes global project health: docs, environment, god modules, and entropy.
    """
    penalty = 0
    issues: List[str] = []

    missing_docs = scan_project_docs(
        path, cast(List[str], profile.get("required_files", []))
    )
    if missing_docs:
        penalty += len(missing_docs) * 15
        issues.append(f"Missing Critical Agent Docs: {', '.join(missing_docs)}")

    health = auditor.check_environment_health(path)
    if not health.get("pyproject_valid", True):
        penalty += 20
        issues.append("Malformed pyproject.toml detected")

    graph, _ = get_import_graph(path)
    inbound = dependencies.get_inbound_imports(graph)
    god_modules = [mod for mod, count in inbound.items() if count > 50]
    if god_modules:
        penalty += len(god_modules) * 10
        issues.append(f"God Modules Detected (Inbound > 50): {', '.join(god_modules)}")

    entropy_stats = auditor.get_crowded_directories(path, threshold=50)
    if entropy_stats:
        penalty += len(entropy_stats) * 5
        issues.append(
            f"High Directory Entropy (>50 files): {', '.join(entropy_stats.keys())}"
        )

    cycles = dependencies.detect_cycles(graph)
    if cycles:
        penalty += len(cycles) * 5
        issues.append(f"Circular Dependencies Detected: {len(cycles)}")

    return penalty, issues


def perform_analysis(
    path: str,
    agent: str = "generic",
    limit_to_files: Optional[List[str]] = None,
    profile: Optional[Dict[str, Any]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
    report_style: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> AnalysisResult:
    """
    Orchestrates the full project analysis pipeline with Context Economics and Custom Reporting.
    """
    if profile is None:
        profile = PROFILES.get(agent, PROFILES["generic"])

    project_root = (
        path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    )
    # Collect all analyzable files (Python and Markdown)
    analyzable_files = dependencies.collect_python_files(path)
    all_files = analyzable_files[:]

    # Build graph and calculate cumulative tokens (Context Economics)
    graph, individual_tokens = get_import_graph(path)
    cumulative_tokens_map = dependencies.calculate_context_tokens(
        graph, individual_tokens
    )

    if limit_to_files is not None:
        analyzable_files = [
            f
            for f in analyzable_files
            if any(f.endswith(changed) for changed in limit_to_files)
        ]

    file_results: List[FileAnalysisResult] = []
    file_scores: List[int] = []

    for filepath in analyzable_files:
        rel_path = os.path.relpath(filepath, start=project_root)
        cum_tokens = cumulative_tokens_map.get(rel_path, 0)

        analyzer = get_analyzer(filepath)
        lang = analyzer.language

        # Merge global thresholds with language-specific overrides if available
        active_thresholds = (thresholds or {}).copy()
        if config:
            lang_cfg = config.get(lang.lower(), {})
            lang_thresholds = lang_cfg.get("thresholds", {})
            active_thresholds.update(lang_thresholds)

        score, issues, loc, complexity, type_safety, metrics_data = analyzer.score_file(
            filepath,
            profile,
            thresholds=active_thresholds,
            cumulative_tokens=cum_tokens,
        )
        file_scores.append(score)

        file_results.append(
            {
                "file": rel_path,
                "language": lang,
                "score": score,
                "issues": issues,
                "loc": loc,
                "complexity": complexity,
                "type_coverage": type_safety,
                "function_metrics": metrics_data,
                "tokens": individual_tokens.get(
                    rel_path, auditor.count_python_tokens(filepath)
                ),
                "cumulative_tokens": cum_tokens,
                "acl": max([m["acl"] for m in metrics_data]) if metrics_data else 0.0,
            }
        )

    penalty, project_issues = get_project_issues(project_root, all_files, profile)
    project_score = max(0, 100 - penalty)
    avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    return {
        "file_results": file_results,
        "final_score": final_score,
        "missing_docs": scan_project_docs(
            project_root, cast(List[str], profile.get("required_files", []))
        ),
        "project_issues": project_issues,
        "dep_analysis": {
            "cycles": dependencies.detect_cycles(graph),
            "god_modules": {
                m: c
                for m, c in dependencies.get_inbound_imports(graph).items()
                if c > 50
            },
        },
        "directory_stats": [
            {"path": p, "file_count": c}
            for p, c in auditor.get_crowded_directories(path, threshold=50).items()
        ],
        "report_style": report_style,
    }
