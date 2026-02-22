from typing import List, Dict, Any, Optional, Union, cast
from .constants import DEFAULT_THRESHOLDS
from .types import FileAnalysisResult, AnalysisResult, AdvisorFileResult


def _generate_summary_section(
    final_score: float, profile: Dict[str, Any], project_issues: Optional[List[str]]
) -> str:
    """
    Creates the executive summary section of the report.

    Args:
        final_score (float): The overall project score.
        profile (Dict[str, Any]): The agent profile used.
        project_issues (Optional[List[str]]): List of project-level issues.

    Returns:
        str: Markdown string for the summary section.
    """
    summary = "# Agent Scorecard Report\n\n"
    summary += f"**Target Agent Profile:** {profile.get('description', 'Generic').split('.')[0]}\n"
    summary += f"**Overall Score: {final_score:.1f}/100** - {'PASS' if final_score >= 70 else 'FAIL'}\n\n"

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


def _generate_acl_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    thresholds: Dict[str, Any],
) -> str:
    """
    Analyzes and reports on units with high Agent Cognitive Load.

    Args:
        stats (Union[List[FileAnalysisResult], List[Dict[str, Any]]]): File analysis statistics.
        thresholds (Dict[str, Any]): Scoring thresholds.

    Returns:
        str: Markdown string for the ACL section.
    """
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


def _generate_type_safety_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    thresholds: Dict[str, Any],
    verbosity: str = "detailed",
) -> str:
    """
    Summarizes type hint coverage across the project.

    Args:
        stats (Union[List[FileAnalysisResult], List[Dict[str, Any]]]): File analysis statistics.
        thresholds (Dict[str, Any]): Scoring thresholds.
        verbosity (str): Output verbosity level (default: "detailed").

    Returns:
        str: Markdown string for the type safety section.
    """
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


def _format_craft_prompt(
    context: str, request: str, actions: List[str], frame: str, template: str
) -> str:
    """
    Formats a prompt using the CRAFT framework (Context, Request, Actions, Frame, Template).
    """
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
    """
    Generates structured CRAFT prompts for systemic remediation.
    """
    acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
    acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])
    type_safety_threshold = thresholds.get(
        "type_safety", DEFAULT_THRESHOLDS["type_safety"]
    )

    prompts = "## 🤖 Agent Prompts for Remediation (CRAFT Format)\n\n"

    if project_issues:
        for issue in project_issues:
            if "God Module" in issue:
                mods = issue.split(": ")[1].split(", ")
                for mod in mods:
                    prompts += f"### Project Issue: God Module `{mod}`\n"
                    prompts += (
                        _format_craft_prompt(
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
                _format_craft_prompt(
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

        if f_res.get("type_coverage", 0) < type_safety_threshold:
            prompts += f"### File: `{file_path}` - Low Type Safety\n"
            prompts += (
                _format_craft_prompt(
                    context="You are a Python Developer focused on static analysis.",
                    request=f"Add PEP 484 type hints to `{file_path}`.",
                    actions=[
                        "Analyze functions missing explicit type signatures.",
                        "Add comprehensive type hints to arguments and return values.",
                        "Use the `typing` module for complex structures.",
                    ],
                    frame=f"Target {type_safety_threshold}% type coverage. Do not change runtime logic.",
                    template="The full updated content of the Python file.",
                )
                + "\n\n"
            )

    return prompts


def _generate_file_table_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    verbosity: str = "detailed",
) -> str:
    """
    Creates a breakdown of analysis for every file.
    """
    if verbosity == "summary":
        table = "### 📂 Failing File Analysis\n\n"
    else:
        table = "### 📂 Full File Analysis\n\n"

    table += "| File | Score | Issues |\n"
    table += "| :--- | :---: | :--- |\n"
    has_rows = False
    for res in stats:
        score = res.get("score", 0)
        if verbosity == "summary" and score >= 70:
            continue
        status = "✅" if score >= 70 else "❌"
        table += f"| {res['file']} | {score} {status} | {res.get('issues', '')} |\n"
        has_rows = True

    if not has_rows and verbosity == "summary":
        return "### 📂 File Analysis\n\n✅ All files passed!\n"

    return table


def generate_markdown_report(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    final_score: float,
    path: str,
    profile: Dict[str, Any],
    project_issues: Optional[List[str]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
    verbosity: str = "detailed",
) -> str:
    """
    Orchestrates the Markdown report generation.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.copy()

    summary = _generate_summary_section(final_score, profile, project_issues)

    if verbosity == "quiet":
        return summary + "\n---\n*Generated by Agent-Scorecard*"

    targets = _generate_acl_section(stats, thresholds)
    types_section = _generate_type_safety_section(stats, thresholds, verbosity)
    prompts = generate_prompts_section(stats, thresholds, project_issues)
    table = _generate_file_table_section(stats, verbosity)

    return (
        summary
        + targets
        + types_section
        + prompts
        + "\n"
        + table
        + "\n---\n*Generated by Agent-Scorecard*"
    )


def generate_advisor_report(
    stats: Union[List[AdvisorFileResult], List[Dict[str, Any]]],
    dependency_stats: Dict[str, int],
    entropy_stats: Dict[str, int],
    cycles: List[List[str]],
) -> str:
    """
    Generates the advanced Advisor Report based on Agent Physics.
    """
    report = "# 🧠 Agent Advisor Report\n\nAnalysis based on the **Physics of Agent-Code Interaction**.\n\n"

    report += (
        "## 1. Agent Cognitive Load (ACL)\n*Formula: ACL = Complexity + (LOC / 20)*\n\n"
    )
    high_acl_files = sorted(
        [s for s in stats if s.get("acl", 0) > 15],
        key=lambda x: x.get("acl", 0),
        reverse=True,
    )
    if high_acl_files:
        report += "### 🚨 Hallucination Zones (ACL > 15)\n| File | ACL | Complexity | LOC |\n|---|---|---|---|\n"
        for s in high_acl_files:
            report += f"| `{s['file']}` | **{s.get('acl', 0):.1f}** | {s.get('complexity', 0):.1f} | {s.get('loc', 0)} |\n"
    else:
        report += "✅ No Hallucination Zones detected.\n"

    report += "\n## 2. Context Economics\n"
    high_token_files = [f for f in stats if f.get("tokens", 0) > 32000]
    if high_token_files:
        report += "### 🪙 Token Budget (> 32k tokens)\n"
        for f in high_token_files:
            report += f"- `{f['file']}`: {f.get('tokens', 0)} tokens\n"
    else:
        report += "✅ All files within context window limits.\n"

    report += "\n## 3. Dependency Entanglement\n"
    god_modules = sorted(
        {k: v for k, v in dependency_stats.items() if v > 50}.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    if god_modules:
        report += "### 🕸 God Modules\n| File | Inbound Refs |\n|---|---|\n"
        for k, v in god_modules:
            report += f"| `{k}` | {v} |\n"

    if cycles:
        report += "### 🔄 Circular Dependencies\n"
        for cycle in cycles:
            report += f"- {' -> '.join(cycle)} -> {cycle[0]}\n"
    else:
        report += "✅ No Circular Dependencies detected.\n"

    if entropy_stats:
        report += "\n## 4. Directory Entropy\n"
        crowded_dirs = {p: c for p, c in entropy_stats.items() if c > 15}
        if crowded_dirs:
            report += "### 📂 Crowded Directories (> 15 files)\n"
            for p, c in crowded_dirs.items():
                report += f"- `{p}`: {c} files\n"
        else:
            report += "✅ Directory structure is balanced.\n"

    return report


def generate_recommendations_report(
    results: Union[AnalysisResult, List[FileAnalysisResult], Any],
) -> str:
    """
    Creates a RECOMMENDATIONS.md content to guide systemic improvements.
    """
    recommendations = []
    file_list = (
        results.get("file_results", []) if isinstance(results, dict) else results
    )
    missing_docs = results.get("missing_docs", []) if isinstance(results, dict) else []

    for res in file_list:
        if res.get("complexity", 0) > 20:
            recommendations.append(
                {
                    "Finding": f"High Complexity: {res['file']}",
                    "Agent Impact": "Context window overflow.",
                    "Recommendation": "Refactor units.",
                }
            )
        if "Circular dependency" in str(res.get("issues", "")):
            recommendations.append(
                {
                    "Finding": f"Circular Dependency: {res['file']}",
                    "Agent Impact": "Recursive loops.",
                    "Recommendation": "Use DI.",
                }
            )
        if res.get("type_coverage", 100) < 90:
            recommendations.append(
                {
                    "Finding": f"Low Type Safety: {res['file']}",
                    "Agent Impact": "Hallucination of signatures.",
                    "Recommendation": "Add PEP 484 hints.",
                }
            )

    if any(doc.lower() == "agents.md" for doc in missing_docs):
        recommendations.append(
            {
                "Finding": "Missing AGENTS.md",
                "Agent Impact": "Agent guesses repository structure.",
                "Recommendation": "Create AGENTS.md.",
            }
        )

    if not recommendations:
        return "# Recommendations\n\n✅ Your codebase looks Agent-Ready!"

    table = "| Finding | Agent Impact | Recommendation |\n| :--- | :--- | :--- |\n"
    for rec in recommendations:
        table += (
            f"| {rec['Finding']} | {rec['Agent Impact']} | {rec['Recommendation']} |\n"
        )

    return "# Recommendations\n\n" + table