from typing import List, Dict, Any, Optional


def _generate_summary_section(
    final_score: float, profile: Dict[str, Any], project_issues: Optional[List[str]]
) -> str:
    """Creates the executive summary section of the report."""
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
    stats: List[Dict[str, Any]], thresholds: Dict[str, Any]
) -> str:
    """Analyzes and reports on functions with high cognitive load."""
    acl_yellow = thresholds.get("acl_yellow", 10)
    acl_red = thresholds.get("acl_red", 20)

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
            if fn["acl"] > acl_yellow:
                status = "🔴 Red" if fn["acl"] > acl_red else "🟡 Yellow"
                targets += f"| `{fn['name']}` | `{fn['file']}` | {fn['acl']:.1f} | {status} |\n"
        targets += "\n"
    else:
        targets += "✅ No functions with high cognitive load found.\n\n"
    return targets


def _generate_type_safety_section(
    stats: List[Dict[str, Any]], thresholds: Dict[str, Any]
) -> str:
    """Summarizes type hint coverage across the project."""
    type_safety_threshold = thresholds.get("type_safety", 90)

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
    """Formats a prompt using the CRAFT framework for high-quality LLM output."""
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


def _generate_prompts_section(
    stats: List[Dict[str, Any]],
    thresholds: Dict[str, Any],
    project_issues: Optional[List[str]] = None,
) -> str:
    """Generates structured CRAFT prompts for remediation."""
    acl_yellow = thresholds.get("acl_yellow", 10)
    acl_red = thresholds.get("acl_red", 20)
    type_safety_threshold = thresholds.get("type_safety", 90)

    prompts = "## 🤖 Agent Prompts for Remediation (CRAFT Format)\n\n"

    # 1. Project-Wide Remediation
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
                                "Extract logic into smaller, cohesive sub-modules.",
                                "Refactor imports to maintain internal dependencies.",
                            ],
                            frame="Inbound imports must stay below 50. Maintain existing functionality.",
                            template="A refactoring plan followed by the new module code structure.",
                        )
                        + "\n\n"
                    )

    # 2. File-Specific Remediation
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
                    context="You are a Senior Software Engineer specializing in code maintainability.",
                    request=f"Refactor high-complexity functions in `{file_path}`.",
                    actions=[
                        f"Target functions with Red ACL (>{acl_red}): {fn_names}.",
                        "Extract nested logic into smaller private helper functions.",
                        f"Target an ACL score < {acl_yellow} for all units.",
                    ],
                    frame="Keep functions under 50 lines. Ensure all tests pass.",
                    template="Markdown code blocks for the refactored functions.",
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


def _generate_file_table_section(stats: List[Dict[str, Any]]) -> str:
    """Creates a full breakdown of analysis for every file."""
    table = "### 📂 Full File Analysis\n\n"
    table += "| File | Score | Issues |\n"
    table += "| :--- | :---: | :--- |\n"
    for res in stats:
        score = res.get("score", 0)
        status = "✅" if score >= 70 else "❌"
        table += f"| {res['file']} | {score} {status} | {res.get('issues', '')} |\n"
    return table


def generate_markdown_report(
    stats: List[Dict[str, Any]],
    final_score: float,
    path: str,
    profile: Dict[str, Any],
    project_issues: Optional[List[str]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
) -> str:
    """Orchestrates the generation of the Markdown report."""
    if thresholds is None:
        thresholds = {"acl_yellow": 10, "acl_red": 20, "type_safety": 90}

    summary = _generate_summary_section(final_score, profile, project_issues)
    targets = _generate_acl_section(stats, thresholds)
    types_section = _generate_type_safety_section(stats, thresholds)
    prompts = _generate_prompts_section(stats, thresholds, project_issues)
    table = _generate_file_table_section(stats)

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
    stats: List[Dict[str, Any]],
    dependency_stats: Dict[str, int],
    entropy_stats: Dict[str, int],
    cycles: List[List[str]],
) -> str:
    """Generates an advanced report focusing on architectural physics."""
    report = "# 🧠 Agent Advisor Report\n\nAnalysis based on the **Physics of Agent-Code Interaction**.\n\n"

    # ACL Physics
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

    # Context Economics
    report += "\n## 2. Context Economics\n"
    high_token_files = [f for f in stats if f.get("tokens", 0) > 32000]
    if high_token_files:
        report += "### 🪙 Token Budget (> 32k tokens)\n"
        for f in high_token_files:
            report += f"- `{f['file']}`: {f.get('tokens', 0)} tokens\n"
    else:
        report += "✅ All files within context window limits.\n"

    # Dependency Entanglement
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

    # Directory Entropy
    if entropy_stats:
        report += "\n## 4. Directory Entropy\n"
        crowded = sorted(entropy_stats.items(), key=lambda x: x[1], reverse=True)
        report += "### 📂 Crowded Directories\n"
        for k, v in crowded:
            report += f"- `{k}`: {v} files\n"

    return report


def generate_recommendations_report(results: Any) -> str:
    """Creates a RECOMMENDATIONS.md file to guide systemic improvements."""
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
                    "Recommendation": "Refactor into pure functions.",
                }
            )

        issues_text = str(res.get("issues", ""))
        if "Circular dependency" in issues_text:
            recommendations.append(
                {
                    "Finding": f"Circular Dependency: {res['file']}",
                    "Agent Impact": "Recursive loops.",
                    "Recommendation": "Use Dependency Injection.",
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
                "Recommendation": "Create AGENTS.md with specific context.",
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
