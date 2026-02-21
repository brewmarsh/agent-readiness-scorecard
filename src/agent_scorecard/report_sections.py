from typing import List, Dict, Any, Optional, Union, cast
from .constants import DEFAULT_THRESHOLDS
from .types import FileAnalysisResult


def generate_summary_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    final_score: float,
    profile: Dict[str, Any],
    project_issues: Optional[List[str]],
) -> str:
    """Creates the executive summary section of the report with aggregated metrics."""
    summary = "# Agent Scorecard Report\n\n"
    summary += f"**Target Agent Profile:** {profile.get('description', 'Generic').split('.')[0]}\n"
    summary += f"**Overall Score: {final_score:.1f}/100** - {'PASS' if final_score >= 70 else 'FAIL'}\n"

    if stats:
        avg_acl = sum(f.get("acl", 0.0) for f in stats) / len(stats)
        avg_type_safety = sum(f.get("type_coverage", 0.0) for f in stats) / len(stats)
        summary += f"**Average ACL:** {avg_acl:.1f}\n"
        summary += f"**Average Type Safety:** {avg_type_safety:.0f}%\n"

    summary += "\n"

    if final_score >= 70:
        summary += "✅ **Status: PASSED** - This codebase is Agent-Ready.\n\n"
    else:
        summary += (
            "❌ **Status: FAILED** - This codebase needs improvement for AI Agents.\n\n"
        )

    if project_issues:
        summary += "### ⚠️ Project Issues\n"
        for issue in project_issues:
            summary += f"- {issue}\n"
        summary += "\n"
    return summary


def generate_acl_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    thresholds: Dict[str, Any],
) -> str:
    """Analyzes and reports on units with high Agent Cognitive Load."""
    acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
    acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])

    targets = "## 🎯 Top Refactoring Targets (Agent Cognitive Load (ACL))\n\n"
    targets += (
        f"ACL = Complexity + (Lines of Code / 20). Target: ACL <= {acl_yellow}.\n\n"
    )

    all_functions = []
    for f_res in stats:
        metrics = f_res.get("function_metrics", [])
        for m in metrics:
            all_functions.append({**m, "file": f_res["file"]})

    top_acl = sorted(all_functions, key=lambda x: x.get("acl", 0), reverse=True)[:10]

    if top_acl:
        targets += "| Function | File | ACL | Status |\n"
        targets += "|----------|------|-----|--------|\n"
        for fn in top_acl:
            acl_val = cast(float, fn.get("acl", 0))
            if acl_val > acl_yellow:
                status = "🔴 Red" if acl_val > acl_red else "🟡 Yellow"
                targets += (
                    f"| `{fn['name']}` | `{fn['file']}` | {acl_val:.1f} | {status} |\n"
                )
        targets += "\n"
    else:
        targets += "✅ No functions with high cognitive load found.\n\n"
    return targets


def generate_type_safety_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    thresholds: Dict[str, Any],
) -> str:
    """Summarizes type hint coverage across the project."""
    type_safety_threshold = thresholds.get(
        "type_safety", DEFAULT_THRESHOLDS["type_safety"]
    )

    types_section = "## 🛡️ Type Safety Index\n\n"
    types_section += f"Target: >{type_safety_threshold}% of functions must have explicit type signatures.\n\n"
    types_section += "| File | Type Safety Index | Status |\n"
    types_section += "| :--- | :---------------: | :----- |\n"

    sorted_types = sorted(stats, key=lambda x: x.get("type_coverage", 0))
    for res in sorted_types:
        coverage = res.get("type_coverage", 0)
        status = "✅" if coverage >= type_safety_threshold else "❌"
        types_section += f"| {res['file']} | {coverage:.0f}% | {status} |\n"

    return types_section + "\n"


def format_craft_prompt(
    context: str, request: str, actions: List[str], frame: str, template: str
) -> str:
    """Formats a prompt using the CRAFT framework (Context, Request, Actions, Frame, Template)."""
    action_items = "\n".join([f"- {a}" for a in actions])
    indented_actions = action_items.replace("\n", "\n> ")
    return (
        f"> **Context**: {context}\n"
        f"> **Request**: {request}\n"
        f"> **Actions**:\n"
        f"> {indented_actions}\n"
        f"> **Frame**: {frame}\n"
        f"> **Template**: {template}"
    )


def generate_prompts_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    thresholds: Dict[str, Any],
    project_issues: Optional[List[str]] = None,
) -> str:
    """Generates structured CRAFT prompts for systemic remediation."""
    acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
    acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])

    prompts = "## 🤖 Agent Prompts for Remediation (CRAFT Format)\n\n"

    if project_issues:
        for issue in project_issues:
            if "God Module" in issue:
                mods = issue.split(": ")[1].split(", ")
                for mod in mods:
                    prompts += f"### Project Issue: God Module `{mod}`\n"
                    prompts += (
                        format_craft_prompt(
                            context="You are a Software Architect specializing in modular system design.",
                            request=f"Decompose the God Module `{mod}` to reduce context pressure.",
                            actions=[
                                "Identify distinct responsibilities within the module.",
                                "Extract logic into cohesive sub-modules.",
                                "Refactor imports to maintain functionality.",
                            ],
                            frame="Inbound imports must stay below 50. Maintain existing logic.",
                            template="A refactoring plan followed by the new module code structure.",
                        )
                        + "\n\n"
                    )

    problematic_files = [f for f in stats if f.get("score", 0) < 90]
    for f_res in problematic_files:
        file_path = f_res["file"]
        metrics = f_res.get("function_metrics", [])
        red_functions = [m for m in metrics if m.get("acl", 0) > acl_red]

        if red_functions:
            fn_names = ", ".join([f"`{m['name']}`" for m in red_functions])
            prompts += f"### File: `{file_path}` - High Cognitive Load\n"
            prompts += (
                format_craft_prompt(
                    context="You are a Senior Python Engineer focused on code maintainability.",
                    request=f"Refactor functions in `{file_path}` with Red ACL scores.",
                    actions=[
                        f"Target functions: {fn_names}.",
                        "Extract nested logic into smaller helper functions.",
                        f"Ensure all units result in an ACL score < {acl_yellow}.",
                    ],
                    frame="Keep functions under 50 lines. Ensure all tests pass.",
                    template="Markdown code blocks for the refactored code.",
                )
                + "\n\n"
            )

    return prompts


def generate_file_table_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
) -> str:
    """Creates a full breakdown of analysis for every file."""
    table = "### 📂 Full File Analysis\n\n"
    table += "| File | Score | Issues |\n"
    table += "| :--- | :---: | :--- |\n"
    for res in stats:
        score = res.get("score", 0)
        status = "✅" if score >= 70 else "❌"
        table += f"| {res['file']} | {score} {status} | {res.get('issues', '')} |\n"
    return table
