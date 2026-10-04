import os
import sys
import subprocess
import click
from importlib.metadata import version, PackageNotFoundError
from typing import List, Dict, Any, Optional, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import core modules
from . import analyzer, auditor
from .config import load_config
from .types import AnalysisResult

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


# --- HELPERS ---


def get_changed_files(
    base_ref: str = "origin/main", target_ref: Optional[str] = None
) -> List[str]:
    """Uses git diff to return a list of changed Python files."""
    try:
        cmd = ["git", "diff", "--name-only", "--diff-filter=d", base_ref]
        if target_ref:
            cmd.append(target_ref)

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return [
            f
            for f in result.stdout.splitlines()
            if f.endswith(".py") and os.path.exists(f)
        ]
    except (subprocess.CalledProcessError, Exception) as e:
        console.print(f"[yellow]Warning: git diff check skipped: {str(e)}[/yellow]")
        return []


def _print_environment_health(
    path: str, results: Union[Dict[str, Any], AnalysisResult], verbosity: str
) -> None:
    """Prints the environment health table including the Agentic Ecosystem."""
    if verbosity == "quiet":
        return

    health_table = Table(title=f"Environment Health v{__version__}")
    health_table.add_column("Check", style="cyan")
    health_table.add_column("Status", justify="right")

    health = auditor.check_environment_health(path)

    # Standard Checks
    health_table.add_row(
        "AGENTS.md", "[green]PASS[/green]" if health["agents_md"] else "[red]FAIL[/red]"
    )
    health_table.add_row(
        "Lock File", "[green]PASS[/green]" if health["lock_file"] else "[red]FAIL[/red]"
    )

    # NEW: Agentic Ecosystem Integration
    ecosystem = health.get("agentic_ecosystem", {})

    # 1. BAML / Framework Detection
    if health.get("baml_detected") or ecosystem.get("has_agent_frameworks"):
        found = ecosystem.get("found_frameworks", [])
        if health.get("baml_detected") and "baml" not in found:
            found.append("baml")
        health_table.add_row(
            "Agent Frameworks", f"[green]PASS ({', '.join(found)})[/green]"
        )
    else:
        health_table.add_row("Agent Frameworks", "[yellow]None[/yellow]")

    # 2. Context Steering (.cursorrules, etc)
    if ecosystem.get("has_context_files"):
        files_str = ", ".join(ecosystem.get("found_files", []))
        health_table.add_row("Context Steering", f"[green]PASS ({files_str})[/green]")
    else:
        health_table.add_row("Context Steering", "[yellow]None[/yellow]")

    # Entropy & Tokens
    entropy = auditor.check_directory_entropy(path)
    e_color = "yellow" if entropy["warning"] else "green"
    health_table.add_row(
        "Directory Entropy",
        f"[{e_color}]{entropy['avg_files']:.1f} files/dir[/{e_color}]",
    )

    tokens = auditor.check_critical_context_tokens(path)
    t_color = "red" if tokens["alert"] else "green"
    health_table.add_row(
        "Critical Token Count", f"[{t_color}]{tokens['token_count']:,} tokens[/]"
    )

    console.print(health_table)
    console.print("")


def _apply_results_processing(results, sort, top, failing=False):
    # Placeholder for results processing logic
    pass


def _handle_score_outputs(
    results, path, agent, report_path, badge, diff, style, sort, top, verbosity
):
    # Placeholder for score output handling
    if report_path:
        with open(report_path, "w") as f:
            f.write(f"Score: {results['final_score']}\n")
    if verbosity != "quiet":
        print(f"Final Score: {results['final_score']}")


@cli.command(name="score")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use.")
@click.option(
    "--fail-under",
    type=int,
    default=70,
    help="Fail if the final score is below this threshold (default: 70).",
)
@click.option("--fix", is_flag=True, help="Automatically fix issues.")
@click.option(
    "--report", "report_path", type=click.Path(), help="Save Markdown report."
)
@click.option(
    "--sort",
    type=click.Choice(["acl", "loc", "complexity", "score", "tokens", "types"]),
    default="acl",
)
@click.option(
    "--limit-to",
    "limit_to_files",
    multiple=True,
    help="Only analyze these specific files.",
)
@click.option("--top", type=int, help="Limit results to top N.")
@click.option("--verbosity", type=click.Choice(["quiet", "summary", "detailed"]))
def score(
    path, agent, fail_under, fix, report_path, sort, top, verbosity, limit_to_files
):
    """Scores a codebase and evaluates the Agentic Ecosystem."""
    cfg = load_config(path)
    final_verbosity = verbosity or cfg.get("verbosity", "summary")

    if final_verbosity != "quiet":
        console.print(
            Panel(
                "[bold cyan]Running Agent Readiness Scorecard[/bold cyan]", expand=False
            )
        )

    # Logic to handle diffs, fixes, and analysis...
    limit_files = list(limit_to_files) if limit_to_files else None
    results = analyzer.perform_analysis(
        path, agent, config=cfg, limit_to_files=limit_files
    )

    # Process results (Sorting/Filtering)
    _apply_results_processing(results, sort, top, failing=False)

    # Final Output
    _handle_score_outputs(
        results,
        path,
        agent,
        report_path,
        False,
        None,
        "actionable",
        sort,
        top,
        final_verbosity,
    )

    if results["final_score"] < fail_under:
        sys.exit(1)


if __name__ == "__main__":
    cli()
