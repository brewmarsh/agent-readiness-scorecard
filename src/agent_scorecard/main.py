import os
import sys
import ast
import click
import mccabe
from rich.console import Console
from rich.table import Table
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

# --- ANALYZERS ---

def get_loc(filepath):
    """Returns lines of code excluding whitespace/comments roughly."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip() and not line.strip().startswith("#"))
    except UnicodeDecodeError:
        return 0

def get_complexity_score(filepath, threshold):
    """Returns (average_complexity, penalty)."""
    try:
        code = open(filepath, "r", encoding="utf-8").read()
        tree = ast.parse(code, filepath)
    except (SyntaxError, UnicodeDecodeError):
        return 0, 0

    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)

    complexities = [graph.complexity() for graph in visitor.graphs.values()]
    if not complexities:
        return 0, 0

    avg_complexity = sum(complexities) / len(complexities)
    penalty = 10 if avg_complexity > threshold else 0
    return avg_complexity, penalty

def check_type_hints(filepath, threshold):
    """Returns (coverage_percent, penalty)."""
    try:
        code = open(filepath, "r", encoding="utf-8").read()
        tree = ast.parse(code)
    except (SyntaxError, UnicodeDecodeError):
        return 0, 0

    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    if not functions:
        return 100, 0

    typed_functions = 0
    for func in functions:
        has_return = func.returns is not None
        has_args = any(arg.annotation is not None for arg in func.args.args)
        if has_return or has_args:
            typed_functions += 1

    coverage = (typed_functions / len(functions)) * 100
    penalty = 20 if coverage < threshold else 0
    return coverage, penalty

def scan_project_docs(root_path, required_files):
    """Checks for existence of agent-critical markdown files."""
    missing = []
    # Normalize checking logic to look in the root of the provided path
    root_files = [f.lower() for f in os.listdir(root_path)] if os.path.isdir(root_path) else []

    for req in required_files:
        if req.lower() not in root_files:
            missing.append(req)
    return missing

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

def score_file(filepath, profile):
    """Calculates score based on the selected profile."""
    score = 100
    details = []

    # 1. Lines of Code
    loc = get_loc(filepath)
    limit = profile["max_loc"]
    if loc > limit:
        # -1 point per 10 lines over limit
        excess = loc - limit
        loc_penalty = (excess // 10)
        score -= loc_penalty
        details.append(f"LOC {loc} > {limit} (-{loc_penalty})")

    # 2. Complexity
    avg_comp, comp_penalty = get_complexity_score(filepath, profile["max_complexity"])
    score -= comp_penalty
    if comp_penalty:
        details.append(f"Complexity {avg_comp:.1f} > {profile['max_complexity']} (-{comp_penalty})")

    # 3. Type Hints
    type_cov, type_penalty = check_type_hints(filepath, profile["min_type_coverage"])
    score -= type_penalty
    if type_penalty:
        details.append(f"Types {type_cov:.0f}% < {profile['min_type_coverage']}% (-{type_penalty})")

    return max(score, 0), ", ".join(details)

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
        project_score -= penalty

    # 2. File Level Check
    py_files = []
    if os.path.isfile(path):
        if path.endswith(".py"): py_files = [path]
    else:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    file_results = []
    for filepath in py_files:
        score, issues = score_file(filepath, profile)
        rel_path = os.path.relpath(filepath, start=path if os.path.isdir(path) else os.path.dirname(path))
        file_results.append({
            "file": rel_path,
            "score": score,
            "issues": issues
        })

    # 3. Aggregation
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

@click.command()
@click.argument("path_or_cmd", default=".", required=False)
@click.argument("extra_path", default=None, required=False)
@click.option("--agent", default="generic", help="Profile to use: generic, jules, copilot.")
@click.option("--fix", is_flag=True, help="Automatically fix common issues.")
@click.option("--badge", is_flag=True, help="Generate an SVG badge for the score.")
@click.option("--output", type=click.Path(), help="Path to save the Markdown report (for 'advise' command).")
def cli(path_or_cmd, extra_path, agent, fix, badge, output):
    """Analyze code compatibility for specific AI Agents."""

    command = "score"
    path = path_or_cmd

    if path_or_cmd == "advise":
        command = "advise"
        path = extra_path or "."
    elif path_or_cmd == "score": # Optional explicit score command
        command = "score"
        path = extra_path or "."

    if not os.path.exists(path):
        console.print(f"[bold red]Path does not exist: {path}[/bold red]")
        sys.exit(2)

    if agent not in PROFILES:
        console.print(f"[bold red]Unknown agent profile: {agent}. using generic.[/bold red]")
        agent = "generic"

    profile = PROFILES[agent]

    if command == "score":
        if fix:
            console.print(Panel(f"[bold cyan]Applying Fixes[/bold cyan]\nProfile: {agent.upper()}", expand=False))
            apply_fixes(path, profile)
            console.print("")

        results = perform_analysis(path, agent)

        console.print(Panel(f"[bold cyan]Running Agent Scorecard[/bold cyan]\nProfile: {agent.upper()}\n{profile['description']}", expand=False))

        if results["missing_docs"]:
            penalty = len(results["missing_docs"]) * 15
            console.print(f"\n[bold yellow]⚠ Missing Critical Agent Docs:[/bold yellow] {', '.join(results['missing_docs'])} (-{penalty} pts)")

        table = Table(title="File Analysis")
        table.add_column("File", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Issues", style="magenta")

        for res in results["file_results"]:
            status_color = "green" if res["score"] >= 70 else "red"
            table.add_row(res["file"], f"[{status_color}]{res['score']}[/{status_color}]", res["issues"])

        console.print(table)
        console.print(f"\n[bold]Final Agent Score: {results['final_score']:.1f}/100[/bold]")

        if badge:
            output_path = "agent_score.svg"
            svg_content = generate_badge(results["final_score"])
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
            console.print(f"[bold green][Generated][/bold green] Badge saved to ./{output_path}")
            console.print(f"\nMarkdown Snippet:\n[![Agent Score]({output_path})](./{output_path})")

        if results["final_score"] < 70:
            console.print("[bold red]FAILED: Not Agent-Ready[/bold red]")
            sys.exit(1)
        else:
            console.print("[bold green]PASSED: Agent-Ready[/bold green]")

    elif command == "advise":
        results = perform_analysis(path, agent)
        report = generate_markdown_report(results)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(report)
            console.print(f"[bold green][Generated][/bold green] Report saved to {output}")
        else:
            console.print(report)

def generate_markdown_report(results):
    """Formats analysis results into a Markdown string."""
    profile = results["profile"]
    md = f"# Agent Scorecard Report\n\n"
    md += f"**Target Agent Profile:** {results['agent'].upper()}\n"
    md += f"**Description:** {profile['description']}\n\n"
    md += f"## Final Score: {results['final_score']:.1f}/100\n\n"

    if results["final_score"] >= 70:
        md += "✅ **Status: PASSED** - This codebase is Agent-Ready.\n\n"
    else:
        md += "❌ **Status: FAILED** - This codebase needs improvement for AI Agents.\n\n"

    if results["missing_docs"]:
        md += "### ⚠ Missing Critical Documentation\n"
        for doc in results["missing_docs"]:
            md += f"- `{doc}` (-15 pts)\n"
        md += "\n"

    md += "### 📂 File Analysis\n\n"
    md += "| File | Score | Issues |\n"
    md += "| :--- | :---: | :--- |\n"
    for res in results["file_results"]:
        status = "✅" if res["score"] >= 70 else "❌"
        md += f"| {res['file']} | {res['score']} {status} | {res['issues']} |\n"

    md += "\n---\n*Generated by Agent-Scorecard*"
    return md

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

if __name__ == "__main__":
    cli()
