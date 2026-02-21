import os
import sys
import copy
import click
from importlib.metadata import version, PackageNotFoundError
from typing import List, Dict, Any, Optional, Union, cast
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import core modules
from . import analyzer, report, auditor
from .prompt_analyzer import PromptAnalyzer
from .config import load_config
from .constants import PROFILES
from .fix import apply_fixes
from .scoring import generate_badge
from .types import AnalysisResult, AdvisorFileResult
from .utils import get_changed_files

console = Console()

# --- VERSION SETUP ---
try:
    __version__ = version("agent-scorecard")
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
@click.version_option(version=__version__)
def cli() -> None:
    """Main entry point for the agent-scorecard CLI."""
    pass


# --- HELPERS ---

def _print_environment_health(
    path: str, results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
    """Prints the environment health table."""
    if verbosity == "quiet":
        return

    health_table = Table(title="Environment Health")
    health_table.add_column("Check", style="cyan")
    health_table.add_column("Status", justify="right")

    health = auditor.check_environment_health(path)
    health_table.add_row(
        "AGENTS.md", "[green]PASS[/green]" if health["agents_md"] else "[red]FAIL[/red]"
    )
    health_table.add_row(
        "Linter Config",
        "[green]PASS[/green]" if health["linter_config"] else "[red]FAIL[/red]",
    )
    health_table.add_row(
        "Lock File", "[green]PASS[/green]" if health["lock_file"] else "[red]FAIL[/red]"
    )

    entropy = auditor.check_directory_entropy(path)
    status = f"{entropy['avg_files']:.1f} files/dir"
    if entropy["warning"] and entropy.get("max_files", 0) > 50:
        status = f"Max {entropy['max_files']} files/dir"

    color = "yellow" if entropy["warning"] else "green"
    health_table.add_row("Directory Entropy", f"[{color}]{status}[/{color}]")

    tokens = auditor.check_critical_context_tokens(path)
    t_color = "red" if tokens["alert"] else "green"
    health_table.add_row(
        "Critical Token Count", f"[{t_color}]{tokens['token_count']:,} tokens[/]"
    )

    console.print(health_table)
    console.print("")


def _print_project_issues(
    results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
    """Prints project-wide issues."""
    if verbosity == "quiet":
        return

    issues = results.get("project_issues", [])
    if not issues:
        return

    table = Table(title="Project Issues Detected", style="red")
    table.add_column("Issue Description", style="red")

    for issue in issues:
        table.add_row(issue)

    console.print(table)
    console.print("")


def _print_file_analysis(
    results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
    """Prints the file analysis table based on verbosity."""
    if verbosity == "quiet":
        return

    table = Table(title="File Analysis")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", style="magenta")

    has_rows = False
    for res in results["file_results"]:
        if verbosity == "summary" and res["score"] == 100:
            continue
        color = "green" if res["score"] >= 70 else "red"
        table.add_row(res["file"], f"[{color}]{res['score']}[/{color}]", res["issues"])
        has_rows = True

    if has_rows:
        console.print(table)


def _print_rich_prompt_analysis(result: Dict[str, Any], filename: str) -> None:
    """Prints a styled report for LLM prompt analysis."""
    console.print(Panel(f"[bold cyan]Prompt Analysis: {filename}[/bold cyan]", expand=False))
    table = Table(title="Heuristic Checks")
    table.add_column("Heuristic", style="cyan")
    table.add_column("Status", justify="right")

    for key, passed in result["results"].items():
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        table.add_row(key.replace("_", " ").title(), status)

    console.print(table)
    if result["improvements"]:
        console.print("\n[bold yellow]Suggested Improvements:[/bold yellow]")
        for imp in result["improvements"]:
            console.print(f"- {imp}")

    score_color = "green" if result["score"] >= 80 else "red"
    console.print(f"\n[bold]Prompt Score: [{score_color}]{result['score']}/100[/{score_color}][/bold]")
    if result["score"] < 80:
        sys.exit(1)


# --- COMMANDS ---

@cli.command(name="check-prompts")
@click.argument("path", required=True)
@click.option("--plain", is_flag=True, help="Output plain text results.")
def check_prompts(path: str, plain: bool) -> None:
    """Static analysis for LLM prompts."""
    try:
        content = sys.stdin.read() if path == "-" else open(path, "r", encoding="utf-8").read()
    except Exception as e:
        console.print(f"[red]Error reading prompt file: {e}[/red]")
        sys.exit(1)

    result = PromptAnalyzer().analyze(content)
    if plain:
        # Fallback to simple printing for CI logs
        print(f"Prompt Score: {result['score']}/100")
        for key, val in result["results"].items(): print(f"{key}: {val}")
    else:
        _print_rich_prompt_analysis(result, path)


@cli.command(name="fix")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
def fix(path: str, agent: str) -> None:
    """Automatically fix issues using configuration thresholds."""
    cfg = load_config(path)
    profile = copy.deepcopy(PROFILES.get(agent, PROFILES["generic"]))
    if cfg.get("thresholds"):
        cast(Dict[str, Any], profile.setdefault("thresholds", {})).update(cast(Dict[str, Any], cfg["thresholds"]))

    console.print(Panel(f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}", expand=False))
    apply_fixes(path, profile)
    console.print("[bold green]Fixes applied![/bold green]")


@cli.command(name="score")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
@click.option("--fix", is_flag=True, help="Automatically fix issues.")
@click.option("--report", "report_path", type=click.Path(), help="Save Markdown report.")
@click.option("--verbosity", type=click.Choice(["quiet", "summary", "detailed"]), help="Override verbosity.")
@click.option("--badge", is_flag=True, help="Generate SVG badge.")
@click.option("--diff", "diff_base", help="Ref to diff against (e.g. origin/main).")
def score(path: str, agent: str, fix: bool, report_path: str, verbosity: str, badge: bool, diff_base: Optional[str]) -> None:
    """Scores a codebase based on agent compatibility."""
    cfg = load_config(path)
    final_verbosity = verbosity or cfg.get("verbosity", "summary")
    thresholds = cast(Dict[str, Any], cfg.get("thresholds"))

    if final_verbosity != "quiet":
        console.print(Panel("[bold cyan]Running Agent Scorecard[/bold cyan]", expand=False))

    if fix:
        apply_fixes(path, copy.deepcopy(PROFILES.get(agent, PROFILES["generic"])))

    limit_files = get_changed_files(diff_base) if diff_base else None
    results = analyzer.perform_analysis(path, agent, thresholds=thresholds, limit_to_files=limit_files)

    _print_environment_health(path, results, final_verbosity)
    _print_project_issues(results, final_verbosity)
    _print_file_analysis(results, final_verbosity)

    score_color = "green" if results["final_score"] >= 70 else "red"
    console.print(f"\n[bold]Final Agent Score: [{score_color}]{results['final_score']:.1f}/100[/{score_color}][/bold]")

    if badge:
        with open("agent_score.svg", "w", encoding="utf-8") as f:
            f.write(generate_badge(results["final_score"]))

    if report_path:
        content = report.generate_markdown_report(cast(List[Dict[str, Any]], results["file_results"]), results["final_score"], path, PROFILES[agent], thresholds=thresholds)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

    if results["final_score"] < 70 or results.get("missing_docs"):
        sys.exit(1)


@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--output", "-o", "output_file", type=click.Path(), help="Save advice to Markdown.")
def advise(path: str, output_file: Optional[str]) -> None:
    """Detailed advice based on Agent Physics."""
    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))
    cfg = load_config(path)
    results = analyzer.perform_analysis(path, "generic", thresholds=cast(Dict[str, Any], cfg.get("thresholds")))

    stats: List[AdvisorFileResult] = []
    for res in results.get("file_results", []):
        tokens = auditor.check_critical_context_tokens(os.path.join(path, res["file"]))
        m_acl = max([m["acl"] for m in res.get("function_metrics", [])] or [0.0])
        stats.append(cast(AdvisorFileResult, {**res, "acl": m_acl, "tokens": tokens["token_count"]}))

    report_md = report.generate_advisor_report(
        stats=cast(List[Dict[str, Any]], stats),
        dependency_stats=results.get("dep_analysis", {}).get("god_modules", {}),
        entropy_stats={d["path"]: d["file_count"] for d in results.get("directory_stats", [])},
        cycles=results.get("dep_analysis", {}).get("cycles", [])
    )

    if output_file:
        dest = os.path.abspath(output_file)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(report_md if stats else "# Advisor Report\n\nNo Python files found.")
        console.print(f"[bold green]Report saved to {dest}[/bold green]")
    else:
        console.print(Markdown(report_md) if 'Markdown' in globals() else report_md)


if __name__ == "__main__":
    cli()