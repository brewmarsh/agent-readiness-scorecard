import os
from typing import List, Dict, Any, Optional
from . import analyzer

def _generate_summary_section(final_score: float, profile: Dict[str, Any], project_issues: Optional[List[str]]) -> str:
    summary = f"# Agent Scorecard Report\n\n"
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
    targets = "## 🎯 Top Refactoring Targets (Agent Cognitive Load (ACL))\n\n"
    targets += "ACL = Complexity + (Lines of Code / 20). Target: ACL <= 10.\n\n"

    all_functions = []
    # stats is the list of file_results dictionaries
    for f_res in stats:
        # Check if function_metrics exists (from Upgrade logic) or we need to derive it
        metrics = f_res.get("function_metrics", [])
        if not metrics and 'acl_violations' in f_res:
             # Fallback if full metrics aren't passed, use violations
             metrics = f_res['acl_violations']
        
        for m in metrics:
            all_functions.append({**m, "file": f_res["file"]})

    # Sort by ACL descending
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
    types_section = "## 🛡️ Type Safety Index\n\n"
    types_section += "Target: >90% of functions must have explicit type signatures.\n\n"

    types_section += "| File | Type Safety Index | Status |\n"
    types_section += "| :--- | :---------------: | :----- |\n"
    
    # Sort by lowest coverage first
    sorted_types = sorted(stats, key=lambda x: x["type_coverage"])
    
    for res in sorted_types:
        status = "✅" if res["type_coverage"] >= 90 else "❌"
        types_section += f"| {res['file']} | {res['type_coverage']:.0f}% | {status} |\n"
    types_section += "\n"
    return types_section

def _generate_prompts_section(stats: List[Dict[str, Any]]) -> str:
    prompts = "## 🤖 Agent Prompts for Remediation\n\n"

    problematic_files = [f for f in stats if f["score"] < 90]

    for f_res in problematic_files:
        file_path = f_res["file"]
        file_issues = []

        # Function metrics might be inside the dict
        metrics = f_res.get("function_metrics", [])
        red_functions = [m for m in metrics if m["acl"] > 20]

        if red_functions:
            fn_names = ", ".join([f"`{m['name']}`" for m in red_functions])
            file_issues.append(f"- **Critical ACL**: Functions {fn_names} have Red ACL (>20). Prompt: 'Refactor functions in `{file_path}` with high cognitive load to bring ACL below 10. Split complex logic and reduce function length.'")

        if f_res["type_coverage"] < 90:
             file_issues.append(f"- **Type Safety**: Coverage is {f_res['type_coverage']:.0f}%. Prompt: 'Add explicit type signatures to all functions in `{file_path}` to meet the 90% Type Safety Index requirement.'")

        if file_issues:
            prompts += f"### File: `{file_path}`\n"
            prompts += "\n".join(file_issues) + "\n\n"

    if not problematic_files:
        prompts += "✅ Codebase is optimized for AI Agents. No immediate prompts needed.\n\n"
    return prompts

def _generate_file_table_section(stats: List[Dict[str, Any]]) -> str:
    table = "### 📂 Full File Analysis\n\n"
    table += "| File | Score | Issues |\n"
    table += "| :--- | :---: | :--- |\n"
    for res in stats:
        status = "✅" if res["score"] >= 70 else "❌"
        table += f"| {res['file']} | {res['score']} {status} | {res['issues']} |\n"
    return table

def generate_markdown_report(stats: List[Dict[str, Any]], final_score: float, path: str, profile: Dict[str, Any], project_issues: Optional[List[str]] = None) -> str:
    """Generates a Markdown report from the collected statistics."""
    summary = _generate_summary_section(final_score, profile, project_issues)
    targets = _generate_acl_section(stats)
    types_section = _generate_type_safety_section(stats)
    prompts = _generate_prompts_section(stats)
    table = _generate_file_table_section(stats)

    return summary + targets + types_section + prompts + "\n" + table + "\n---\n*Generated by Agent-Scorecard*"

def generate_advisor_report(stats: List[Dict[str, Any]], dependency_stats: Dict[str, int], entropy_stats: Dict[str, int], cycles: List[List[str]]) -> str:
    """Generates a detailed Advisor Report based on Agent Physics."""

    report = "# 🧠 Agent Advisor Report\n\n"
    report += "Analysis based on the **Physics of Agent-Code Interaction**.\n\n"

    # --- 1. Agent Cognitive Load (ACL) ---
    report += "## 1. Agent Cognitive Load (ACL)\n"
    report += "Agents have a limited reasoning budget. High ACL burns tokens on logic instead of task execution.\n"
    report += "*Formula: ACL = Complexity + (LOC / 20)*\n\n"

    high_acl_files = [s for s in stats if s.get('acl', 0) > 15]
    high_acl_files.sort(key=lambda x: x.get('acl', 0), reverse=True)

    if high_acl_files:
        report += "### 🚨 Hallucination Zones (ACL > 15)\n"
        report += "These files are too complex for reliable agent reasoning.\n\n"
        report += "| File | ACL | Complexity | LOC |\n"
        report += "|---|---|---|---|\n"
        for s in high_acl_files:
            report += f"| `{s['file']}` | **{s['acl']:.1f}** | {s['complexity']:.1f} | {s['loc']} |\n"
    else:
        report += "✅ No Hallucination Zones detected. Code is within reasoning limits.\n"
    report += "\n"

    # --- 2. Dependency Entanglement ---
    report += "## 2. Dependency Entanglement\n"
    report += "Complex graphs confuse agent planning capabilities.\n\n"

    # God Modules
    god_modules = {k: v for k, v in dependency_stats.items() if v > 50}
    if god_modules:
        report += "### 🕸 God Modules (Inbound Imports > 50)\n"
        report += "These files appear too often in the context window.\n\n"
        report += "| File | Inbound Refs |\n"
        report += "|---|---|\n"
        sorted_gods = sorted(god_modules.items(), key=lambda x: x[1], reverse=True)
        for k, v in sorted_gods:
             report += f"| `{k}` | {v} |\n"
    else:
         report += "✅ No God Modules detected.\n"
    report += "\n"

    # Circular Dependencies
    if cycles:
        report += "### 🔄 Circular Dependencies\n"
        report += "Infinite recursion risks during planning.\n\n"
        for cycle in cycles:
             report += f"- {' -> '.join(cycle)} -> {cycle[0]}\n"
    else:
        report += "✅ No Circular Dependencies detected.\n"
    report += "\n"

    # --- 3. Context Economics ---
    report += "## 3. Context Economics\n"
    report += "Optimizing the retrieval and context window budget.\n\n"

    # MERGE: Preserved Token Budget logic from Beta branch
    high_token_files = [f for f in stats if f.get("tokens", 0) > 32000]
    if high_token_files:
        report += "### 🪙 Token Budget (> 32k tokens)\n"
        report += "⚠ **Files exceeding token budget:**\n\n"
        for f in high_token_files:
             report += f"- `{f['file']}`: {f['tokens']} tokens\n"
        report += "\n"

    if entropy_stats:
        report += "### 📂 Directory Entropy (Files > 50)\n"
        report += "Large directories confuse retrieval tools.\n\n"
        report += "| Directory | File Count |\n"
        report += "|---|---|\n"
        sorted_entropy = sorted(entropy_stats.items(), key=lambda x: x[1], reverse=True)
        for k, v in sorted_entropy:
            report += f"| `{k}/` | {v} |\n"
    else:
        report += "✅ Directory entropy is low.\n"

    return report

def generate_recommendations_report(results: Any) -> str:
    """Generates a RECOMMENDATIONS.md content based on analysis results."""
    recommendations = []

    # 1. High ACL (> 20)
    # Check if 'file_results' key exists, else assume results IS the list
    file_list = results.get("file_results", []) if isinstance(results, dict) else results

    for res in file_list:
        if res["complexity"] > 20:
            recommendations.append({
                "Finding": f"High Complexity in {res['file']}",
                "Agent Impact": "Context window overflow.",
                "Recommendation": "Refactor into pure functions."
            })

    # 2. Missing AGENTS.md
    if isinstance(results, dict) and results.get("missing_docs"):
        if any(doc.lower() == "agents.md" for doc in results["missing_docs"]):
            recommendations.append({
                "Finding": "Missing AGENTS.md",
                "Agent Impact": "Agent guesses commands.",
                "Recommendation": "Create AGENTS.md with build steps."
            })

    # 3. Circular Dependency
    for res in file_list:
        if "circular" in str(res.get("issues", "")).lower():
            recommendations.append({
                "Finding": f"Circular Dependency in {res['file']}",
                "Agent Impact": "Infinite recursion loops.",
                "Recommendation": "Use Dependency Injection."
            })

    # 4. Type Coverage < 90%
    for res in file_list:
        if res["type_coverage"] < 90:
            recommendations.append({
                "Finding": f"Type Coverage < 90% in {res['file']}",
                "Agent Impact": "Hallucination of signatures.",
                "Recommendation": "Add PEP 484 hints."
            })

    if not recommendations:
        return "# Recommendations\n\n✅ No recommendations at this time. Your codebase looks Agent-Ready!"

    table = "| Finding | Agent Impact | Recommendation |\n"
    table += "| :--- | :--- | :--- |\n"
    for rec in recommendations:
        table += f"| {rec['Finding']} | {rec['Agent Impact']} | {rec['Recommendation']} |\n"

    return "# Recommendations\n\n" + table
