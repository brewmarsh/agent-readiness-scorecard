import os
import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import common modules (Added auditor)
from . import analyzer, report, auditor

# Use the Modular Refactor (Beta Branch)
from .constants import PROFILES
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

    # 3. Environment Health & Auditor Checks (From Auditor Branch)
    health_table = Table(title="Environment Health")
    health_table.add_column("Check", style="cyan")
    health_table.add_column("Status", justify="right")

    # Use the auditor module for environment checks
    health = auditor.check_environment_health(path)
    health_table.add_row("AGENTS.md", "[green]PASS[/green]" if health["agents_md"] else "[red]FAIL[/red]")
    health_table.add_row("Linter Config", "[green]PASS[/green]" if health["linter_config"] else "[red]FAIL[/red]")
    health_table.add_row("Lock File", "[green]PASS[/green]" if health["lock_file"] else "[red]FAIL[/red]")

    entropy = auditor.check_directory_entropy(path)
    if entropy["warning"] and entropy.get("max_files", 0) > 50:
        entropy_status = f"Max {entropy['max_files']} files/dir"
    else:
        entropy_status = f"{entropy['avg_files']:.1f} files/dir"

    entropy_color = "yellow" if entropy["warning"] else "green"
    health_table.add_row("Directory Entropy", f"[{entropy_color}]{entropy_status}[/{entropy_color}]")

    tokens = auditor.check_critical_context_tokens(path)
    token_color = "red" if tokens["alert"] else "green"
    health_table.add_row("Critical Token Count", f"[{token_color}]{tokens['token_count']:,}[/{token_color}]")

    # Dependency Analysis (Visual check for Health Table)
    import_graph = analyzer.get_import_graph(path)
    cycles = analyzer.detect_cycles(import_graph)
    if cycles:
        health_table.add_row("Circular Dependencies", f"[red]DETECTED ({len(cycles)})[/red]")
    else:
        health_table.add_row("Circular Dependencies", "[green]NONE[/green]")

    console.print(health_table)
    console.print("") # Spacing

    # 4. Analyze & Score Files (Beta Logic)
    table = Table(title="File Analysis")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", style="magenta")

    file_scores = []
    stats = []
    
    for filepath in py_files:
        # Use the imported modular function for basic scoring
        s_score, notes = score_file(filepath, profile)
        file_scores.append(s_score)
        
        # Gather detailed stats for the report
        if report_file:
            # RESOLUTION: Use Beta logic (Function-level stats)
            func_stats = analyzer.get_function_stats(filepath)
            # Identify functions that are too complex (ACL > 15)
            acl_violations = [f for f in func_stats if f['acl'] > 15]
            
            stats.append({
                "file": os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path)),
                "loc": analyzer.get_loc(filepath),
                "complexity": analyzer.get_complexity_score(filepath),
                "type_coverage": analyzer.check_type_hints(filepath),
                "acl_violations": acl_violations
            })

        status_color = "green" if s_score >= 70 else "red"
        rel_path = os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path))
        table.add_row(rel_path, f"[{status_color}]{s_score}[/{status_color}]", notes)

    console.print(table)

    # 5. Project Level Checks (Scoring/Penalty Calculation)
    project_penalty, project_issues = analyzer.get_project_issues(path, py_files, profile)

    for issue in project_issues:
        color = "red" if "God Modules" in issue else "yellow"
        console.print(f"\n[bold {color}]⚠ {issue}[/bold {color}]")

    project_score = max(0, 100 - project_penalty)

    # 6. Final Calculation
    avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0
    final_score = (avg_file_score * 0.8) + (project_score * 0.2)

    console.print(f"\n[bold]Final Agent Score: {final_score:.1f}/100[/bold]")

    # 7. Generate Badge
    if badge:
        output_path = "agent_score.svg"
        svg_content = generate_badge(final_score)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        console.print(f"[bold green][Generated][/bold green] Badge saved to ./{output_path}")
        console.print(f"\nMarkdown Snippet:\n[![Agent Score]({output_path})](./{output_path})")

    # 8. Generate Report
    if report_file:
        markdown_content = report.generate_markdown_report(stats, final_score, path, profile, project_issues=project_issues)
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
    """Generates a Markdown report with actionable advice based on Agent Physics."""
    
    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))
    
    py_files = []
    if os.path.isfile(path) and path.endswith(".py"):
        py_files = [path]
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            if any(part.startswith(".") for part in root.split(os.sep)):
                continue
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    stats = []
    with console.status("[bold green]Analyzing Code Physics...[/bold green]"):
        for filepath in py_files:
            loc = analyzer.get_loc(filepath)
            complexity = analyzer.get_complexity_score(filepath)

            # RESOLUTION: Use Beta logic
            # We calculate ACL at the function level and take the MAX to see how "dangerous" the file is.
            func_stats = analyzer.get_function_stats(filepath)
            max_acl = max((f['acl'] for f in func_stats), default=0)

            stats.append({
                "file": os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path)),
                "loc": loc,
                "complexity": complexity,
                "acl": max_acl
            })

        # Dependency Analysis
        graph = analyzer.get_import_graph(path)
        inbound = analyzer.get_inbound_imports(graph)
        cycles = analyzer.detect_cycles(graph)

        # Entropy Analysis
        entropy = analyzer.get_directory_entropy(path)

    markdown_report = report.generate_advisor_report(stats, inbound, entropy, cycles)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        console.print(f"\n[bold green]Report saved to {output_file}[/bold green]")
    else:
        # Use rich Markdown for pretty printing
        from rich.markdown import Markdown
        console.print(Markdown(markdown_report))

if __name__ == "__main__":
    cli()