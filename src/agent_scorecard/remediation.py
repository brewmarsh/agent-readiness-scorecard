from typing import List, Dict, Any, Optional, Union
from .constants import DEFAULT_THRESHOLDS
from .types import FileAnalysisResult, AnalysisResult


def _format_craft_prompt(
    context: str, request: str, actions: List[str], frame: str, template: str
) -> str:
    """Formats a prompt using the CRAFT framework (Context, Request, Actions, Frame, Template).

    Args:
        context: The context for the prompt.
        request: The specific request.
        actions: List of actions to take.
        frame: The frame or constraints.
        template: The output template.

    Returns:
        The formatted CRAFT prompt string.
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
    """Generates structured CRAFT prompts for systemic remediation.

    Args:
        stats: List of file analysis results.
        thresholds: Dictionary of threshold values.
        project_issues: Optional list of project-wide issues.

    Returns:
        The markdown section for remediation prompts.
    """
    acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
    acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])
    # RESOLUTION: Re-integrated type safety threshold for remediation logic
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

        # RESOLUTION: Type Safety remediation prompt logic re-integrated from Beta branch
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


def generate_recommendations_report(
    results: Union[AnalysisResult, List[FileAnalysisResult], Any],
) -> str:
    """Creates a RECOMMENDATIONS.md file to guide systemic improvements.

    Args:
        results: The analysis results containing file results and issues.

    Returns:
        The content of the RECOMMENDATIONS.md file.
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
