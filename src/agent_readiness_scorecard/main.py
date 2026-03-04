import os
import sys
import subprocess
import copy
import click
from importlib.metadata import version, PackageNotFoundError
from typing import List, Dict, Any, Optional, Union, cast
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

# Import core modules
from . import analyzer, report, auditor
from .prompt_analyzer import PromptAnalyzer
from .config import load_config
from .constants import PROFILES
from .fix import apply_fixes
from .scoring import generate_badge
from .types import AnalysisResult, AdvisorFileResult, FileAnalysisResult

console = Console()

# --- VERSION SETUP ---
try:
    from ._version import __version__
except (ImportError, ModuleNotFoundError):
    try:
        __version__ = version("agent-readiness-scorecard")
    except PackageNotFoundError:
        __version__ = "0.0.0"


# --- CLI DEFINITION ---
class DefaultGroup(click.Group):
    def resolve_command(self, ctx: click.Context, args: List[str]) -> Any:
        """Resolves the command, defaulting to 'score' if no command matches."""
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            if args and not args[0].startswith("-"):
                args.insert(0, "score")
            elif not args:
                args.insert(0, "score")
            return super().resolve_command(ctx, args)


@click.group(cls=DefaultGroup)
@click.version_option(
    version=__version__,
    prog_name="agent-readiness-scorecard",
    message="%(prog)s version %(version)s",
)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Main entry point for the agent-readiness-scorecard CLI."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(".")

# ... [Helpers _print_summary_card, _print_acl_targets, etc. remain unchanged] ...

@cli.command(name="score")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
@click.option("--fix", is_flag=True, help="Automatically fix issues.")
@click.option(
    "--report", "report_path", type=click.Path(), help="Save Markdown report."
)
@click.option(
    "--verbosity",
    type=click.Choice(["quiet", "summary", "detailed"]),
    help="Override verbosity.",
)
@click.option(
    "--report-style",
    type=click.Choice(["full", "actionable", "collapsed"]),
    help="Set the report verbosity style.",
)
@click.option("--badge", is_flag=True, help="Generate SVG badge.")
@click.option(
    "--limit-to", "limit_to", multiple=True, help="Limit analysis to these files."
)
@click.option(
    "--diff",
    is_flag=True,
    help="Analyze only files changed compared to base reference.",
)
@click.option(
    "--diff-base",
    default="origin/main",
    help="Base reference for diff (default: origin/main).",
)
@click.option(
    "--sort",
    type=click.Choice(["acl", "loc", "complexity", "score", "tokens", "types"]),
    default="acl",
    help="Sort results by metric (default: acl).",
)
@click.option(
    "--top",
    type=int,
    help="Limit results (files in console, functions in report).",
)
@click.option(
    "--failing",
    is_flag=True,
    help="Filter results to show only failing files (score < 70).",
)
@click.option(
    "--fail-under",
    type=int,
    default=70,
    help="Fail if the final score is below this threshold (default: 70).",
)
def score(
    path: str,
    agent: str,
    fix: bool,
    report_path: str,
    verbosity: str,
    report_style: Optional[str],
    badge: bool,
    limit_to: tuple,
    diff: bool,
    diff_base: str,
    sort: str,
    top: Optional[int],
    failing: bool,
    fail_under: int,
) -> None:
    # ... [Initial setup and perform_analysis call] ...

    # --- RESOLUTION: SORTING & LIMITING LOGIC ---
    file_results = cast(List[Dict[str, Any]], results["file_results"])

    if failing:
        file_results = [res for res in file_results if res["score"] < 70]

    reverse_map = {
        "acl": True, "loc": True, "complexity": True,
        "score": False, "tokens": True, "types": False,
    }
    key_map = {
        "acl": lambda x: x["acl"],
        "loc": lambda x: x["loc"],
        "complexity": lambda x: x["complexity"],
        "score": lambda x: x["score"],
        "tokens": lambda x: x.get("cumulative_tokens", 0),
        "types": lambda x: x["type_coverage"],
    }

    file_results.sort(key=key_map[sort], reverse=reverse_map[sort])

    if top is not None:
        file_results = file_results[:top]

    results["file_results"] = cast(List[FileAnalysisResult], file_results)
    # --- END SORTING & LIMITING ---

    _print_summary_card(results, final_verbosity)
    _print_acl_targets(results, final_verbosity, thresholds=thresholds)
    _print_type_safety_index(results, final_verbosity, thresholds=thresholds)
    _print_environment_health(path, results, final_verbosity)
    _print_file_analysis(results, final_verbosity)
    _print_project_issues(cast(List[str], results.get("project_issues", [])), final_verbosity)

    score_color = "green" if results["final_score"] >= 70 else "red"
    console.print(f"\n[bold]Final Agent Score: [{score_color}]{results['final_score']:.1f}/100[/{score_color}][/bold]")

    if top is not None and final_verbosity != "quiet":
        console.print(f"\n[dim]Showing top {top} issues. Run without --top to see the full list.[/dim]")

    if report_path:
        # RESOLUTION: Combined Feature branch metadata (version/sort) with Beta branch summary data
        content = report.generate_markdown_report(
            cast(List[Dict[str, Any]], results["file_results"]),
            results["final_score"],
            path,
            PROFILES[agent],
            project_issues=cast(List[str], results.get("project_issues", [])),
            thresholds=thresholds,
            report_style=final_report_style,
            version=__version__,
            sort_by=sort,
            top_limit=top,
            summary=cast(Dict[str, int], results.get("summary")),
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

    if results["final_score"] < fail_under or results.get("project_issues"):
        sys.exit(1)