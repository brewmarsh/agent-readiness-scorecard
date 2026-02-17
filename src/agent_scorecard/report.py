import os
from typing import List, Dict, Any, Optional

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

    top_acl = sorted(all_functions, key=lambda x: x.get('acl', 0), reverse=True)[:10]

    if top_acl:
        targets += "| Function | File | ACL | Status |\n"
        targets += "|----------|------|-----|--------|\n"
        for fn in top_acl:
            if fn.get('acl', 0) > 10:
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

    sorted_types = sorted(stats, key=lambda x: x.get("type_coverage", 0))

    for res in sorted_types:
        coverage = res.get("type_coverage", 0)
        status = "✅" if coverage >= 90 else "❌"
        types_section += f"| {res['file']} | {coverage:.0f}% | {status} |\n"
    types_section += "\n"
    return types_section

def _build_craft_prompt(issue_type: str, file_path: str, details: str) -> str:
    """Helper function to build a CRAFT-structured remediation prompt."""
    context = "You are a Senior Python Refactoring Specialist."
    request = f"Your goal is to refactor `{file_path}` to resolve {issue_type} issues: {details}."

    if issue_type == "ACL":
        actions = "1. Analyze the complexity. 2. Extract nested logic into helper functions. 3. Ensure no function exceeds 20 lines."
    else:  # Type Safety
        actions = "1. Analyze function signatures. 2. Add specific type hints (avoid Any). 3. Verify imports."

    frame = "Do not break existing logic. Do not remove comments unless necessary."
    template = "Output the refactored code in a single Markdown code block."

    return (
        f"**Context**: {context}\n"
        f"**Request**: {request}\n"
        f"**Actions**: {actions}\n"
        f"**Frame**: {frame}\n"
        f"**Template**: {template}"
    )

def _generate_prompts_section(stats: List[Dict[str, Any]]) -> str:
    """Provides actionable prompts for an AI Agent to use for refactoring."""
    prompts = "## 🤖 Agent Prompts for Remediation\n\n"
    problematic_files = [f for f in stats if f.get("score", 100) < 90]

    for f_res in problematic_files:
        file_path = f_res["file"]
        file_issues = []

        metrics = f_res.get("function_metrics", [])
        red_functions = [m for m in metrics if m.get("acl", 0) > 20]

        if red_functions:
            fn_names = ", ".join([f"`{m['name']}`" for m in red_functions])
            prompt = _build_craft_prompt("ACL", file_path, f"Functions {fn_names} have Red ACL (>20)")
            file_issues.append(f"- **Critical ACL**: Functions {fn_names} have Red ACL (>20).\n\n{prompt}")

        coverage = f_res.get("type_coverage", 0)
        if coverage < 90:
             prompt = _build_craft_prompt("Type Safety", file_path, f"Coverage is {coverage:.0f}%")
             file_issues.append(f"- **Type Safety**: Coverage is {coverage:.0f}%.\n\n{prompt}")

        if file_issues:
            prompts += f"### File: `{file_path}`\n"
            prompts += "\n".join(file_issues) + "\n\n"

    if not problematic_files:
        prompts += "✅ Codebase is optimized for AI Agents. No immediate prompts needed.\n\n"
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

def generate_markdown_report(stats: List[Dict[str, Any]], final_score: float, path: str, profile: Dict[str, Any], project_issues: Optional[List[str]] = None) -> str:
    """Orchestrates the generation of the Markdown report."""
    summary = _generate_summary_section(final_score, profile, project_issues)
    targets = _generate_acl_section(stats)
    types_section = _generate_type_safety_section(stats)
    prompts = _generate_prompts_section(stats)
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
            report += f"| `{s['file']}` | **{s.get('acl', 0):.1f}** | {s.get('complexity', 0):.1f} | {s.get('loc', 0)} |\n"
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
             report += f"- `{f['file']}`: {f.get('tokens', 0)} tokens\n"

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
    file_list = []
    missing_docs = []

    if isinstance(results, dict):
        file_list = results.get("file_results", [])
        missing_docs = results.get("missing_docs", [])
    elif isinstance(results, list):
        file_list = results

    for res in file_list:
        if res.get("complexity", 0) > 20:
            recommendations.append({
                "Finding": f"High Complexity in {res['file']}",
                "Agent Impact": "Context window overflow.",
                "Recommendation": "Refactor into pure functions."
            })
        if "Circular dependency detected" in res.get("issues", ""):
            recommendations.append({
                "Finding": f"Circular Dependency in {res['file']}",
                "Agent Impact": "Infinite recursion loops.",
                "Recommendation": "Refactor to use dependency injection or a shared interface."
            })
        if res.get("type_coverage", 100) < 90:
            recommendations.append({
                "Finding": f"Type Coverage < 90% in {res['file']}",
                "Agent Impact": "Hallucination of signatures.",
                "Recommendation": "Add explicit type hints."
            })

    if any(doc.lower() == "agents.md" for doc in missing_docs):
        recommendations.append({
            "Finding": "Missing AGENTS.md",
            "Agent Impact": "Agent guesses commands.",
            "Recommendation": "Create AGENTS.md with build steps."
        })

    if not recommendations:
        return "# Recommendations\n\n✅ Your codebase looks Agent-Ready!"

    table = "| Finding | Agent Impact | Recommendation |\n"
    table += "| :--- | :--- | :--- |\n"
    for rec in recommendations:
        table += f"| {rec['Finding']} | {rec['Agent Impact']} | {rec['Recommendation']} |\n"

    return "# Recommendations\n\n" + table
