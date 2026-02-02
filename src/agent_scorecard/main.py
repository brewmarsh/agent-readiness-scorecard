import os
import sys
import ast
import click
import mccabe
from rich.console import Console
from rich.table import Table
from . import analyzer, report
from rich.panel import Panel

console = Console()

# --- CONSTANTS ---
AGENT_CONTEXT_TEMPLATE = """# Agent Context: {project_name}

## Project Goal
[Brief description of what this project does]

## Architecture
- **Entry Point:** [Main file]
- **Key Modules:**
    - `module_a`: Handles X
    - `module_b`: Handles Y

## Developer Constraints
- Use Python 3.10+
- All functions must have docstrings
- Type hints are strict
"""

INSTRUCTIONS_TEMPLATE = """# Instructions

1. **Install Dependencies:** `pip install -r requirements.txt`
2. **Run Tests:** `pytest`
3. **Lint:** `pylint src/`
"""

TYPE_HINT_STUB = "# TODO: Add type hints for Agent clarity"
DOCSTRING_TEXT = '"""TODO: Add docstring for AI context."""'

# --- AGENT PROFILES ---
PROFILES = {
    "generic": {
        "max_loc": 200,
        "max_complexity": 10,
        "min_type_coverage": 50,
        "required_files": ["README.md"],
        "description": "Standard cleanliness checks."
    },
    "jules": {
        "max_loc": 150,  # Stricter LOC for autonomy
        "max_complexity": 8,
        "min_type_coverage": 80,  # High typing requirement
        "required_files": ["agents.md", "instructions.md"],
        "description": "Strict typing and autonomy instructions."
    },
    "copilot": {
        "max_loc": 100,  # Very small chunks preferred
        "max_complexity": 15, # Lenient on logic, strict on size
        "min_type_coverage": 40,
        "required_files": [],
        "description": "Optimized for small context completion."
    }
}


# --- FIX LOGIC ---

def fix_file_issues(filepath):
    """Injects docstrings and type hint TODOs where missing."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        code = "".join(lines)
        tree = ast.parse(code)
    except (SyntaxError, UnicodeDecodeError):
        return

    insertions = [] # List of (line_index, text)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check for missing docstring
            if not ast.get_docstring(node):
                # Insert after the function definition line (handling decorators)
                # The body starts at node.body[0].lineno.
                # We need to insert *before* the first statement of the body.

                body_start_line = node.body[0].lineno - 1 # 0-indexed

                # Determine indentation from the first line of the body
                body_line_content = lines[body_start_line]
                body_indent = len(body_line_content) - len(body_line_content.lstrip())
                indent_str = body_line_content[:body_indent] # Preserve tab vs space

                # Check if it's just 'pass' or '...' on the same line (rare but possible)
                # If body[0].lineno is same as node.lineno (e.g. def foo(): pass), simpler to skip or handle carefully.
                if node.body[0].lineno > node.lineno:
                     insertions.append((body_start_line, f"{indent_str}{DOCSTRING_TEXT}\n"))

            # Check for 0% type hints
            has_return = node.returns is not None
            has_args = any(arg.annotation is not None for arg in node.args.args)
            if not has_return and not has_args:
                # Insert comment above function definition
                # Start line is node.lineno - 1 (0-indexed)
                # BUT if decorators exist, we want to go above them.
                start_line = node.lineno - 1
                if node.decorator_list:
                    start_line = node.decorator_list[0].lineno - 1

                # Check idempotency: peek at line before start_line
                # Use strict check to avoid re-adding if already present
                prev_line_idx = start_line - 1
                if prev_line_idx >= 0 and TYPE_HINT_STUB in lines[prev_line_idx]:
                    continue

                # Determine function indentation
                func_line_content = lines[node.lineno-1]
                func_indent = len(func_line_content) - len(func_line_content.lstrip())
                indent_str = func_line_content[:func_indent]

                insertions.append((start_line, f"{indent_str}{TYPE_HINT_STUB}\n"))

    if not insertions:
        return

    # Sort insertions by line number descending to keep indices valid
    # Also handle multiple insertions at same line (e.g. type hint + something else? unlikely here but safe)
    # Using stable sort with reverse=True handles order.
    insertions.sort(key=lambda x: x[0], reverse=True)

    for line_idx, text in insertions:
        lines.insert(line_idx, text)

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)

    console.print(f"[bold green][Fixed][/bold green] Injected issues in {filepath}")

def apply_fixes(path, profile):
    """Applies fixes to project files and structure."""

    # 1. Project Docs
    if os.path.isdir(path):
        required = profile.get("required_files", [])
        existing = [f.lower() for f in os.listdir(path)]

        for req in required:
            if req.lower() not in existing:
                filepath = os.path.join(path, req)
                content = ""
                if req.lower() == "agents.md":
                    content = AGENT_CONTEXT_TEMPLATE.format(project_name=os.path.basename(os.path.abspath(path)))
                elif req.lower() == "instructions.md":
                    content = INSTRUCTIONS_TEMPLATE
                elif req.lower() == "readme.md":
                    content = "# Project\n\nAuto-generated README."

                if content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    console.print(f"[bold green][Fixed][/bold green] Created {req}")

    # 2. File Fixes
    py_files = []
    if os.path.isfile(path) and path.endswith(".py"):
        py_files = [path]
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    for py_file in py_files:
        fix_file_issues(py_file)


# --- CORE LOGIC ---

def _calculate_final_score(stats, path, profile=PROFILES['generic']):
    """Helper to calculate the final score from stats."""

    file_scores = []
    for s in stats:
        score = 100
        # LOC penalty
        if s['loc'] > profile['max_loc']:
            score -= (s['loc'] - profile['max_loc']) // 10
        # Complexity penalty
        if s['complexity'] > profile['max_complexity']:
            score -= 10
        # Type coverage penalty
        if s['type_coverage'] < profile['min_type_coverage']:
            score -= 20
        file_scores.append(max(0, score))

    avg_file_score = sum(file_scores) / len(file_scores) if file_scores else 0

    missing_docs = analyzer.scan_project_docs(path, profile['required_files'])
    project_penalty = len(missing_docs) * 15
    project_score = 100 - project_penalty

    return (avg_file_score * 0.8) + (project_score * 0.2)

def _score_file_from_stats(stats, profile):
    """Calculates score and notes for a single file from its stats."""
    score = 100
    details = []

    # LOC
    limit = profile["max_loc"]
    if stats['loc'] > limit:
        excess = stats['loc'] - limit
        loc_penalty = (excess // 10)
        score -= loc_penalty
        details.append(f"LOC {stats['loc']} > {limit} (-{loc_penalty})")

    # Complexity
    if stats['complexity'] > profile['max_complexity']:
        comp_penalty = 10
        score -= comp_penalty
        details.append(f"Complexity {stats['complexity']:.1f} > {profile['max_complexity']} (-{comp_penalty})")

    # Type Hints
    if stats['type_coverage'] < profile['min_type_coverage']:
        type_penalty = 20
        score -= type_penalty
        details.append(f"Types {stats['type_coverage']:.0f}% < {profile['min_type_coverage']}% (-{type_penalty})")

    return max(score, 0), ", ".join(details)

@click.group()
def cli():
    """Main entry point for the agent-scorecard CLI."""
    pass

@cli.command(name="score")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--agent", default="generic", help="Profile to use: generic, jules, copilot.")
@click.option("--fix", is_flag=True, help="Automatically fix common issues.")
@click.option("--badge", is_flag=True, help="Generate an SVG badge for the score.")
@click.option("--report", "report_path", type=click.Path(), help="Save the report to a Markdown file.")
def score(path, agent, fix, badge, report_path):
    """Scores a codebase based on AI-agent compatibility."""

    if agent not in PROFILES:
        console.print(f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]")
        agent = "generic"

    profile = PROFILES[agent]

    if fix:
        console.print(Panel(f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}", expand=False))
        apply_fixes(path, profile)
        console.print("") # Newline

    console.print(Panel(f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}", expand=False))

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
        stats.append({
            "file": os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path)),
            "loc": analyzer.get_loc(filepath),
            "complexity": analyzer.get_complexity_score(filepath),
            "type_coverage": analyzer.check_type_hints(filepath)
        })

    table = Table(title="File Analysis")
    table.add_column("File", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", style="magenta")

    rows = []
    for s in stats:
        score, notes = _score_file_from_stats(s, profile)
        rows.append((s['file'], score, notes))
        status_color = "green" if score >= 70 else "red"
        table.add_row(s['file'], f"[{status_color}]{score}[/{status_color}]", notes)

    console.print(table)

    missing_docs = analyzer.scan_project_docs(path, profile["required_files"])
    if missing_docs:
        console.print(f"\n[bold yellow]⚠ Missing Critical Agent Docs:[/bold yellow] {', '.join(missing_docs)}")

    final_score = _calculate_final_score(stats, path, profile)

    console.print(f"\n[bold]Final Agent Score: {final_score:.1f}/100[/bold]")

    if badge:
        output_path = "agent_score.svg"
        svg_content = generate_badge(final_score)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        console.print(f"[bold green][Generated][/bold green] Badge saved to ./{output_path}")
        console.print(f"\nMarkdown Snippet:\n[![Agent Score]({output_path})](./{output_path})")

    if report_path:
        # Generate Markdown report
        markdown_report = f"# Agent Scorecard Report\n\n"
        markdown_report += f"**Final Score: {final_score:.1f}/100** - {'PASS' if final_score >= 70 else 'FAIL'}\n\n"
        markdown_report += "| File | Score | Issues |\n"
        markdown_report += "|---|---|---|\n"

        for file, score, notes in rows:
            markdown_report += f"| {file} | {score} | {notes or 'None'} |\n"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        console.print(f"\n[bold green]Report saved to {report_path}[/bold green]")

    if final_score < 70:
        console.print("[bold red]FAILED: Not Agent-Ready[/bold red]")
        sys.exit(1)
    else:
        console.print("[bold green]PASSED: Agent-Ready[/bold green]")


def generate_badge(score):
    """Generates an SVG badge for the agent score."""
    if score >= 90:
        color = "#4c1"  # Bright Green
    elif score >= 70:
        color = "#dfb317"  # Yellow/Orange
    else:
        color = "#e05d44"  # Red

    score_str = f"{int(score)}/100"

    # Constants for SVG generation
    left_width = 70
    right_width = 50
    total_width = left_width + right_width
    height = 20
    border_radius = 3

    # SVG template using f-strings
    svg_template = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{height}" role="img" aria-label="Agent Score: {score_str}">
    <title>Agent Score: {score_str}</title>
    <linearGradient id="s" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="r">
        <rect width="{total_width}" height="{height}" rx="{border_radius}" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
        <rect width="{left_width}" height="{height}" fill="#555"/>
        <rect x="{left_width}" width="{right_width}" height="{height}" fill="{color}"/>
        <rect width="{total_width}" height="{height}" fill="url(#s)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
        <text aria-hidden="true" x="{left_width * 10 / 2}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(left_width - 10) * 10}">Agent Score</text>
        <text x="{left_width * 10 / 2}" y="140" transform="scale(.1)" fill="#fff" textLength="{(left_width - 10) * 10}">Agent Score</text>
        <text aria-hidden="true" x="{(left_width + right_width / 2) * 10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(right_width - 10) * 10}">{score_str}</text>
        <text x="{(left_width + right_width / 2) * 10}" y="140" transform="scale(.1)" fill="#fff" textLength="{(right_width - 10) * 10}">{score_str}</text>
    </g>
</svg>
"""
    return svg_template.strip()


@cli.command(name="advise")
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--output", "-o", "output_file", type=click.Path(), help="Save the report to a Markdown file.")
def advise(path, output_file):
    """Generates a Markdown report with actionable advice."""

    console.print(Panel("[bold cyan]Running Advisor Mode[/bold cyan]", expand=False))

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
        stats.append({
            "file": os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path)),
            "loc": analyzer.get_loc(filepath),
            "complexity": analyzer.get_complexity_score(filepath),
            "type_coverage": analyzer.check_type_hints(filepath)
        })

    # Calculate the final score
    profile = PROFILES['generic']
    final_score = _calculate_final_score(stats, path, profile)

    markdown_report = report.generate_markdown_report(stats, final_score, path, profile)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        console.print(f"\n[bold green]Report saved to {output_file}[/bold green]")
    else:
        console.print("\n" + markdown_report)

if __name__ == "__main__":
    cli()
