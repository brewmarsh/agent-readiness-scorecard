import os
from typing import List, Dict, Any, Optional
from . import analyzer

def _generate_summary_section(final_score: float, profile: Dict[str, Any], project_issues: Optional[List[str]]) -> str:
    """Creates the executive summary section of the report."""
    summary = "# Agent Scorecard Report\n\n"
    summary += f"**Target Agent Profile:** {profile.get('description', 'Generic').split('.')[0]}\n"
    summary += f"**Overall Score: {final_score:.1f}/100** - {'PASS' if final_score >= 70 else 'FAIL'}\n\n"

    if final_score >= 70:
        summary += "✅ **Status: PASSED** - This codebase is Agent-Ready.\n\n"
    else:
        summary += "❌ **Status: FAILED** - This codebase needs improvement for AI Agents.\n\n"

    if project_issues:
        summary += "### ⚠️ Project Issues\n"
        for issue in project_issues:
            summary += f"- {issue}\n"
        summary += "\n"
    return summary

def _generate_acl_section(stats: List[Dict[str, Any]]) -> str:
    """Analyzes and reports on functions with high cognitive load."""
    targets = "## 🎯 Top Refactoring Targets (Agent Cognitive Load (ACL))\n\n"
    targets += "ACL = Complexity + (Lines of Code / 20). Target: ACL <= 10.\n\n"

    all_functions = []
    for f_res in stats:
        metrics = f_res.get("function_metrics", [])
        if not metrics and 'acl_violations' in f_res:
             metrics = f_res['acl_violations']

        for m in metrics:
            all_functions.append({**m, "file": f_res["file"]})

    top_acl = sorted(all_functions, key=lambda x: x['acl'], reverse=True)[:10]

    if top_acl:
        targets += "| Function | File | ACL | Status |\n"
        targets += "|----------|------|-----|--------|\n"
        for fn in top_acl:
            if fn['acl'] > 10:
                status = "🔴 Red" if fn['acl'] > 20 else "🟡 Yellow"
                targets += f"| `{fn['name']}` | `{fn['file']}` | {fn['acl']:.1f} | {status} |\n"
        targets += "\n"
    else:
        targets += "✅ No functions with high cognitive load found.\n\n"
    return targets

def _generate_type_safety_section(stats: List[Dict[str, Any]]) -> str:
    """Summarizes type hint coverage across the project."""
    types_section = "## 🛡️ Type Safety Index\n\n"
    types_section += "Target: >90% of functions must have explicit type signatures.\n\n"

    types_section += "| File | Type Safety Index | Status |\n"
    types_section += "| :--- | :---------------: | :----- |\n"

    sorted_types = sorted(stats, key=lambda x: x["type_coverage"])

    for res in sorted_types:
        status = "✅" if res["type_coverage"] >= 90 else "❌"
        types_section += f"| {res['file']} | {res['type_coverage']:.0f}% | {status} |\n"
    types_section += "\n"
    return types_section

def _format_craft_prompt(context: str, request: str, actions: List[str], frame: str, template: str) -> str:
    """Formats a prompt using the CRAFT framework."""
    action_items = "\n".join([f"- {a}" for a in actions])
    return (
        f"> **Context**: {context}\n"
        f"> **Request**: {request}\n"
        f"> **Actions**:\n"
        f"> {action_items.replace('\n', '\n> ')}\n"
        f"> **Frame**: {frame}\n"
        f"> **Template**: {template}"
    )

def _generate_prompts_section(stats: List[Dict[str, Any]], project_issues: Optional[List[str]] = None) -> str:
    """Provides actionable prompts for an AI Agent to use for refactoring."""
    prompts = "## 🤖 Agent Prompts for Remediation (CRAFT Format)\n\n"
    prompts += "Copy and paste these prompts into your favorite LLM (ChatGPT, Claude, Cursor) to fix the issues.\n\n"

    # 1. Project-Wide Issues (God Modules)
    if project_issues:
        for issue in project_issues:
            if "God Modules Detected" in issue:
                mods = issue.split(": ")[1].split(", ")
                for mod in mods:
                    prompts += f"### Project Issue: God Module `{mod}`\n"
                    craft = _format_craft_prompt(
                        context="You are a Software Architect specializing in modular system design.",
                        request=f"Decompose the God Module `{mod}` to improve maintainability and reduce context pressure.",
                        actions=[
                            "Analyze the module to identify distinct responsibilities.",
                            "Extract logic into smaller, cohesive modules.",
                            "Refactor inbound imports to point to the new, smaller modules."
                        ],
                        frame="Ensure inbound imports for any single module stay below 50. Maintain all existing functionality.",
                        template="A detailed refactoring plan followed by the code for the new module structure."
                    )
                    prompts += craft + "\n\n"

    # 2. File-Specific Issues
    problematic_files = [f for f in stats if f["score"] < 90]

    for f_res in problematic_files:
        file_path = f_res["file"]

        metrics = f_res.get("function_metrics", [])
        red_functions = [m for m in metrics if m["acl"] > 20]

        if red_functions:
            fn_names = ", ".join([f"`{m['name']}`" for m in red_functions])
            prompts += f"### File: `{file_path}` - High Cognitive Load\n"
            craft = _format_craft_prompt(
                context="You are a Senior Software Engineer specializing in code maintainability.",
                request=f"Refactor high-complexity functions in `{file_path}`.",
                actions=[
                    f"Identify functions with Red ACL (>20): {fn_names}.",
                    "Extract complex nested logic into smaller, private helper functions.",
                    "Ensure each function has a single responsibility and ACL < 10."
                ],
                frame="Keep functions under 50 lines. Maintain existing logic and ensure all tests pass.",
                template="Return only the refactored code blocks for the affected functions."
            )
            prompts += craft + "\n\n"

        if f_res["type_coverage"] < 90:
            prompts += f"### File: `{file_path}` - Low Type Safety\n"
            craft = _format_craft_prompt(
                context="You are a Python Developer focused on type safety and static analysis.",
                request=f"Add comprehensive type hints to `{file_path}`.",
                actions=[
                    "Analyze all functions lacking explicit type signatures.",
                    "Add PEP 484 compatible type hints to all function arguments and return values.",
                    "Use `typing` module (List, Dict, Any, Optional) where appropriate."
                ],
                frame="Do not change runtime logic. Target 100% type coverage for this file.",
                template="Return the full updated content of the file."
            )
            prompts += craft + "\n\n"

    if not problematic_files and not (project_issues and any("God Modules" in i for i in project_issues)):
        prompts += "✅ Codebase is optimized for AI Agents. No immediate prompts needed.\n\n"
    return prompts

def _generate_file_table_section(stats: List[Dict[str, Any]]) -> str:
    """Creates a full breakdown of analysis for every file."""
    table = "### 📂 Full File Analysis\n\n"
    table += "| File | Score | Issues |\n"
    table += "| :--- | :---: | :--- |\n"
    for res in stats:
        status = "✅" if res["score"] >= 70 else "❌"
        table += f"| {res['file']} | {res['score']} {status} | {res['issues']} |\n"
    return table

def generate_markdown_report(stats: List[Dict[str, Any]], final_score: float, path: str, profile: Dict[str, Any], project_issues: Optional[List[str]] = None) -> str:
    """Orchestrates the generation of the Markdown report."""
    summary = _generate_summary_section(final_score, profile, project_issues)
    targets = _generate_acl_section(stats)
    types_section = _generate_type_safety_section(stats)
    prompts = _generate_prompts_section(stats, project_issues)
    table = _generate_file_table_section(stats)

    return summary + targets + types_section + prompts + "\n" + table + "\n---\n*Generated by Agent-Scorecard*"

def generate_advisor_report(stats: List[Dict[str, Any]], dependency_stats: Dict[str, int], entropy_stats: Dict[str, int], cycles: List[List[str]]) -> str:
    """Generates an advanced report focusing on architectural 'physics' of agent interaction."""
    report = "# 🧠 Agent Advisor Report\n\n"
    report += "Analysis based on the **Physics of Agent-Code Interaction**.\n\n"

    # 1. Agent Cognitive Load (ACL)
    report += "## 1. Agent Cognitive Load (ACL)\n"
    report += "Agents have a limited reasoning budget. High ACL burns tokens on logic instead of task execution.\n"
    report += "*Formula: ACL = Complexity + (LOC / 20)*\n\n"

    high_acl_files = [s for s in stats if s.get('acl', 0) > 15]
    high_acl_files.sort(key=lambda x: x.get('acl', 0), reverse=True)

    if high_acl_files:
        report += "### 🚨 Hallucination Zones (ACL > 15)\n"
        report += "| File | ACL | Complexity | LOC |\n"
        report += "|---|---|---|---|\n"
        for s in high_acl_files:
            report += f"| `{s['file']}` | **{s['acl']:.1f}** | {s['complexity']:.1f} | {s['loc']} |\n"
    else:
        report += "✅ No Hallucination Zones detected.\n"
    report += "\n"

    # 2. Dependency Entanglement
    report += "## 2. Dependency Entanglement\n"
    god_modules = {k: v for k, v in dependency_stats.items() if v > 50}
    if god_modules:
        report += "### 🕸 God Modules (Inbound Imports > 50)\n"
        report += "| File | Inbound Refs |\n"
        report += "|---|---|\n"
        sorted_gods = sorted(god_modules.items(), key=lambda x: x[1], reverse=True)
        for k, v in sorted_gods:
             report += f"| `{k}` | {v} |\n"
    
    if cycles:
        report += "### 🔄 Circular Dependencies\n"
        for cycle in cycles:
             report += f"- {' -> '.join(cycle)} -> {cycle[0]}\n"
    else:
        report += "✅ No Circular Dependencies detected.\n"
    report += "\n"

    # 3. Context Economics
    report += "## 3. Context Economics\n"
    high_token_files = [f for f in stats if f.get("tokens", 0) > 32000]
    if high_token_files:
        report += "### 🪙 Token Budget (> 32k tokens)\n"
        for f in high_token_files:
             report += f"- `{f['file']}`: {f['tokens']} tokens\n"

    if entropy_stats:
        report += "### 📂 Directory Entropy (Files > 50)\n"
        report += "| Directory | File Count |\n"
        report += "|---|---|\n"
        sorted_entropy = sorted(entropy_stats.items(), key=lambda x: x[1], reverse=True)
        for k, v in sorted_entropy:
            report += f"| `{k}/` | {v} |\n"

    return report

def generate_recommendations_report(results: Any) -> str:
    """Creates a RECOMMENDATIONS.md file to guide systemic project improvements."""
    recommendations = []
    file_list = results.get("file_results", []) if isinstance(results, dict) else results

    for res in file_list:
        if res["complexity"] > 20:
            recommendations.append({
                "Finding": f"High Complexity in {res['file']}",
                "Agent Impact": "Context window overflow.",
                "Recommendation": "Refactor into pure functions."
            })

    if isinstance(results, dict) and results.get("missing_docs"):
        if any(doc.lower() == "agents.md" for doc in results["missing_docs"]):
            recommendations.append({
                "Finding": "Missing AGENTS.md",
                "Agent Impact": "Agent guesses commands.",
                "Recommendation": "Create AGENTS.md with build steps."
            })

    for res in file_list:
        if res.get("type_coverage", 100) < 90:
            recommendations.append({
                "Finding": f"Type Coverage < 90% in {res['file']}",
                "Agent Impact": "Hallucination of signatures.",
                "Recommendation": "Add PEP 484 hints."
            })
        if "Circular dependency detected" in res.get("issues", ""):
            recommendations.append({
                "Finding": f"Circular Dependency in {res['file']}",
                "Agent Impact": "Infinite recursion loops.",
                "Recommendation": "Refactor into a directed graph."
            })

    if not recommendations:
        return "# Recommendations\n\n✅ Your codebase looks Agent-Ready!"

    table = "| Finding | Agent Impact | Recommendation |\n"
    table += "| :--- | :--- | :--- |\n"
    for rec in recommendations:
        table += f"| {rec['Finding']} | {rec['Agent Impact']} | {rec['Recommendation']} |\n"

    return "# Recommendations\n\n" + table