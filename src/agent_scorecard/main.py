import os
import sys
import copy
import click
from importlib.metadata import version, PackageNotFoundError
from typing import List, Dict, Any, Optional, Union, cast
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Import core modules
from . import analyzer, report, auditor
from . import console as output_console
from .prompt_analyzer import PromptAnalyzer
from .config import load_config
from .constants import PROFILES
from .fix import apply_fixes
from .scoring import generate_badge
from .types import AnalysisResult, AdvisorFileResult

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
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Main entry point for the agent-scorecard CLI."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(".")


# --- COMMANDS ---


@cli.command(name="check-prompts")
@click.argument("path", required=True)
@click.option("--plain", is_flag=True, help="Plain output for CI.")
def check_prompts(path: str, plain: bool) -> None:
    """
    Checks a prompt file for LLM best practices.

    Args:
        path (str): Path to the prompt file, or '-' for stdin.
        plain (bool): Whether to use plain output for CI.

    Returns:
        None
    """
    content = ""
    if path == "-":
        content = sys.stdin.read()
    elif os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        console.print(f"[bold red]Error:[/bold red] File not found: {path}")
        sys.exit(2)

    analyzer_inst = PromptAnalyzer()
    result = analyzer_inst.analyze(content)

    output_console.print_prompt_analysis(path, result, plain)

    if result["score"] < 80:
        sys.exit(1)


@cli.command(name="fix")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
def fix(path: str, agent: str) -> None:
    """
    Automatically fix issues using configuration thresholds.

    Args:
        path (str): The path to fix.
        agent (str): The agent profile to use.

    Returns:
        None
    """
    if agent not in PROFILES:
        console.print(
            f"[yellow]Unknown agent profile: {agent}. using generic.[/yellow]"
        )
        agent = "generic"

    cfg = load_config(path)
    profile = copy.deepcopy(PROFILES.get(agent, PROFILES["generic"]))

    if cfg.get("thresholds"):
        cast(Dict[str, Any], profile.setdefault("thresholds", {})).update(
            cast(Dict[str, Any], cfg["thresholds"])
        )

    console.print(
        Panel(
            f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}",
            expand=False,
        )
    )
    apply_fixes(path, profile)
    console.print("[bold green]Fixes applied![/bold green]")


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
@click.option("--badge", is_flag=True, help="Generate SVG badge.")
def score(
    path: str, agent: str, fix: bool, report_path: str, verbosity: str, badge: bool
) -> None:
    """
    Scores a codebase based on agent compatibility.

    Args:
        path (str): The path to score.
        agent (str): The agent profile to use.
        fix (bool): Whether to automatically fix issues.
        report_path (str): Optional path to save a Markdown report.
        verbosity (str): Optional verbosity override.
        badge (bool): Whether to generate an SVG badge.

    Returns:
        None
    """
    if agent not in PROFILES:
        console.print(
            f"[yellow]Unknown agent profile: {agent}. using generic.[/yellow]"
        )
        agent = "generic"

    cfg = load_config(path)
    final_verbosity = verbosity or cfg.get("verbosity", "summary")
    thresholds = cast(Dict[str, Any], cfg.get("thresholds"))

    if final_verbosity != "quiet":
        console.print(
            Panel("[bold cyan]Running Agent Scorecard[/bold cyan]", expand=False)
        )

    if fix:
        console.print(
            Panel(
                f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}",
                expand=False,
            )
        )
        profile = copy.deepcopy(PROFILES.get(agent, PROFILES["generic"]))
        apply_fixes(path, profile)

    results = analyzer.perform_analysis(path, agent, thresholds=thresholds)

    output_console.print_environment_health(path, results, final_verbosity)
    output_console.print_file_analysis(results, final_verbosity)
    output_console.print_project_issues(
        cast(List[str], results.get("project_issues", [])), final_verbosity
    )

    # Always print final score
    score_color = "green" if results["final_score"] >= 70 else "red"
    console.print(
        f"\n[bold]Final Agent Score: [{score_color}]{results['final_score']:.1f}/100[/{score_color}][/bold]"
    )

    if badge:
        svg = generate_badge(results["final_score"])
        with open("agent_score.svg", "w", encoding="utf-8") as f:
            f.write(svg)
        if final_verbosity != "quiet":
            console.print("[bold green]Badge saved to agent_score.svg[/bold green]")

    if report_path:
        content = report.generate_markdown_report(
            cast(List[Dict[str, Any]], results["file_results"]),
            results["final_score"],
            path,
            PROFILES[agent],
            thresholds=thresholds,
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

    if results["final_score"] < 70 or results.get("project_issues"):
        sys.exit(1)


@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option(
    "--output", "-o", "output_file", type=click.Path(), help="Save advice to Markdown."
)
def advise(path: str, output_file: Optional[str]) -> None:
    """
    Detailed advice based on Agent Physics.

    Args:
        path (str): The path to analyze.
        output_file (Optional[str]): Optional path to save advice to Markdown.

    Returns:
        None
    """
    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))
    cfg = load_config(path)
    results = analyzer.perform_analysis(
        path, "generic", thresholds=cast(Dict[str, Any], cfg.get("thresholds"))
    )

    stats: List[AdvisorFileResult] = []
    for res in results.get("file_results", []):
        tokens = auditor.check_critical_context_tokens(os.path.join(path, res["file"]))
        m_acl = max([m["acl"] for m in res.get("function_metrics", [])] or [0.0])
        stats.append(
            cast(
                AdvisorFileResult,
                {**res, "acl": m_acl, "tokens": tokens["token_count"]},
            )
        )

    report_md = report.generate_advisor_report(
        stats=cast(List[Dict[str, Any]], stats),
        dependency_stats=results.get("dep_analysis", {}).get("god_modules", {}),
        entropy_stats={
            d["path"]: d["file_count"] for d in results.get("directory_stats", [])
        },
        cycles=results.get("dep_analysis", {}).get("cycles", []),
    )

    if output_file:
        dest = os.path.abspath(output_file)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(
                report_md if stats else "# Advisor Report\n\nNo Python files found."
            )
        console.print(f"[bold green]Report saved to {dest}[/bold green]")
    else:
        console.print(Markdown(report_md))


if __name__ == "__main__":
    cli()