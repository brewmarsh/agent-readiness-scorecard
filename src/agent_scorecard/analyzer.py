import os
import click
from .constants import PROFILES
from .checks import scan_project_docs
from .scoring import score_file

class DefaultGroup(click.Group):
    """Click group that defaults to 'score' if no subcommand is provided."""
    def __init__(self, *args, **kwargs):
        self.default_command = 'score'
        super().__init__(*args, **kwargs)

    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            if args and not args[0].startswith('-'):
                args.insert(0, self.default_command)
            elif not args:
                args.insert(0, self.default_command)
            return super().resolve_command(ctx, args)

def perform_analysis(path, agent_name):
    """Core analysis logic that returns data for presentation."""
    if agent_name not in PROFILES:
        agent_name = "generic"
    profile = PROFILES[agent_name]

    # 1. Project Level Check
    project_score = 100
    missing_docs = []
    if os.path.isdir(path):
        missing_docs = scan_project_docs(path, profile["required_files"])
        penalty = len(missing_docs) * 15
        project_score = max(0, 100 - penalty)

    # 2. Gather Files
    py_files = []
    if os.path.isfile(path) and path.endswith(".py"):
        py_files = [path]
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    # 3. File Level Check
    file_results = []
    for filepath in py_files:
        score, issues, loc, complexity, type_cov = score_file(filepath, profile)
        rel_path = os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path))
        file_results.append({
            "file": rel_path,
            "score": score,
            "issues": issues,
            "loc": loc,
            "complexity": complexity,
            "type_coverage": type_cov
        })

    # 4. Aggregation
    avg_file_score = sum(f["score"] for f in file_results) / len(file_results) if file_results else 0
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    return {
        "agent": agent_name,
        "profile": profile,
        "final_score": final_score,
        "project_score": project_score,
        "missing_docs": missing_docs,
        "file_results": file_results
    }
