import os
import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import common modules
from . import analyzer, report

# Use the Modular Refactor (Beta Branch)
from .constants import PROFILES
from .checks import scan_project_docs
from .fix import apply_fixes
from .scoring import score_file, generate_badge

console = Console()

class DefaultGroup(click.Group):
    """
    Invokes a default command if a subcommand is not found.
    """
    def parse_args(self, ctx, args):
        if not args:
            args.insert(0, "score")
        elif args[0] not in self.commands and args[0] not in ["--help", "--version", "-h"]:
            args.insert(0, "score")
        return super().parse_args(ctx, args)

@click.group(cls=DefaultGroup, invoke_without_command=True)
@click.version_option(package_name="agent-scorecard")
def cli():
    """Main entry point for the agent-scorecard CLI."""
    pass

@cli.command(name="fix")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use: generic, jules, copilot.")
def fix(path: str, agent: str) -> None:
    """Automatically fixes common issues."""
    if agent not in PROFILES:
        console.print(f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]")
        agent = "generic"

    profile = PROFILES[agent]

    console.print(Panel(f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}", expand=False))
    apply_fixes(path, profile)
    console.print("")  # Newline
    console.print("[bold green]Fixes applied![/bold green]")


@cli.command(name="score")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use: generic, jules, copilot.")
@click.option("--fix", is_flag=True, help="Automatically fix common issues.")
@click.option("--badge", is_flag=True, help="Generate an SVG badge for the score.")
@click.option("--report", "report_file", default=None, help="Generate a Markdown report to the specified file.")
def score(path: str, agent: str, fix: bool, badge: bool, report_file: str) -> None:
    """Scores a codebase based on AI-agent compatibility."""

    if agent not in PROFILES:
        console.print(f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]")
        agent = "generic"

    profile = PROFILES[agent]

    # 1. Run Fixes (if requested)
    if fix:
        console.print(Panel(f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}", expand=False))
        apply_fixes(path, profile)
        console.print("")  # Newline

    console.print(Panel(f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}", expand=False))

    # 2. Gather Files
    py_files = []
    if os.path.isfile(path) and path.endswith(".py"):
        py_files = [path]
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    # 3. Analyze & Score Files
    table = Table(title="File Analysis")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", style="magenta")

    file_scores = []
    stats = []
    
    for filepath in py_files:
        # Use the imported modular function
        s_score, notes = score_file(filepath, profile)
        file_scores.append(s_score)
        
        if report_file:
            loc = analyzer.get_loc(filepath)
            complexity = analyzer.get_complexity_score(filepath)
            stats.append({
                "file": os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path)),
                "loc": loc,
                "complexity": complexity,
                "type_coverage": analyzer.check_type_hints(filepath),
                "acl": analyzer.get_acl_score(loc, complexity)
            })

        status_color = "green" if s_score >= 70 else "red"
        rel_path = os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path))
        table.add_row(rel_path, f"[{status_color}]{s_score}[/{status_color}]", notes)

    console.print(table)

    # 4. Project Level Checks
    # Use the imported modular function
    missing_docs = scan_project_docs(path, profile["required_files"])
    if missing_docs:
        console.print(f"\n[bold yellow]⚠ Missing Critical Agent Docs:[/bold yellow] {', '.join(missing_docs)}")
        project_penalty = len(missing_docs) * 15
        project_score = max(0, 100 - project_penalty)
    else:
        project_score = 100

    # 5. Final Calculation
    avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    console.print(f"\n[bold]Final Agent Score: {final_score:.1f}/100[/bold]")

    # 6. Generate Badge
    if badge:
        output_path = "agent_score.svg"
        # Use the imported modular function
        svg_content = generate_badge(final_score)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        console.print(f"[bold green][Generated][/bold green] Badge saved to ./{output_path}")
        console.print(f"\nMarkdown Snippet:\n[![Agent Score]({output_path})](./{output_path})")

    # 7. Generate Report
    if report_file:
        markdown_content = report.generate_markdown_report(stats, final_score, path, profile)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        console.print(f"\n[bold green]Report saved to {report_file}[/bold green]")

    if final_score < 70:
        console.print("[bold red]FAILED: Not Agent-Ready[/bold red]")
        sys.exit(1)
    else:
        console.print("[bold green]PASSED: Agent-Ready[/bold green]")

@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--output", "-o", "output_file", type=click.Path(), help="Save the report to a Markdown file.")
def advise(path, output_file):
    """Generates a Markdown report with actionable advice."""
    
    # We can reuse the logic here or delegate to report module
    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))
    
    # Simple re-implementation for advice using the report module
    # Assuming report module handles the logic internally
    # For now, we stub this to ensure it calls the imported report generator
    
    # Re-gather stats for the report generator
    # Note: In a full refactor, 'stats' generation should likely be its own function 
    # in analyzer.py, but we will leave this inline logic for safety unless
    # analyzer.get_project_stats() exists.
    
    py_files = []
    if os.path.isfile(path) and path.endswith(".py"):
        py_files = [path]
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    stats = []
    for filepath in py_files:
        loc = analyzer.get_loc(filepath)
        complexity = analyzer.get_complexity_score(filepath)
        stats.append({
            "file": os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path)),
            "loc": loc,
            "complexity": complexity,
            "type_coverage": analyzer.check_type_hints(filepath),
            "acl": analyzer.get_acl_score(loc, complexity)
        })

    final_score = 0 # Placeholder if we don't recalculate
    markdown_report = report.generate_markdown_report(stats, final_score, path, PROFILES['generic'])

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        console.print(f"\n[bold green]Report saved to {output_file}[/bold green]")
    else:
        console.print("\n" + markdown_report)

if __name__ == "__main__":
    cli()
