from typing import List, Dict, Any, Optional, Union, cast
from .constants import DEFAULT_THRESHOLDS
from .types import FileAnalysisResult, AdvisorFileResult
from .remediation import generate_prompts_section, generate_recommendations_report

__all__ = ["generate_recommendations_report", "generate_prompts_section"]


def _generate_summary_section(
    final_score: float, profile: Dict[str, Any], project_issues: Optional[List[str]]
) -> str:
    """
    Creates the executive summary section of the report.
    """
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


def _generate_acl_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    thresholds: Dict[str, Any],
) -> str:
    """
    Analyzes and reports on units with high Agent Cognitive Load.
    """
    acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
    acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])

    targets = "## 🎯 Top Refactoring Targets (Agent Cognitive Load (ACL))\n\n"
    targets += f"ACL = Complexity + (Lines of Code / 20). Target: ACL <= {acl_yellow}.\n\n"

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
                targets += f"| `{fn['name']}` | `{fn['file']}` | {acl_val:.1f} | {status} |\n"
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
    Summarizes type hint coverage using progressive disclosure to reduce noise.
    """
    type_safety_threshold = thresholds.get("type_safety", DEFAULT_THRESHOLDS["type_safety"])

    failing = [s for s in stats if s.get("type_coverage", 0) < type_safety_threshold]
    passing = [s for s in stats if s.get("type_coverage", 0) >= type_safety_threshold]

    types_section = "### 🛡️ Type Safety Index (Action Required)\n\n"
    types_section += f"Target: >{type_safety_threshold}% coverage. \n\n"

    # Actionable Section: Files failing the threshold
    if failing:
        types_section += "| File | Type Safety Index | Status |\n"
        types_section += "| :--- | :---------------: | :----- |\n"
        for res in sorted(failing, key=lambda x: x.get("type_coverage", 0)):
            coverage = res.get("type_coverage", 0)
            types_section += f"| `{res['file']}` | {coverage:.0f}% | ❌ |\n"
        types_section += "\n"
    else:
        types_section += "✅ All files meet type safety requirements.\n\n"

    # Collapsible Section: Hidden in 'summary' verbosity, shown in 'detailed'
    if passing and verbosity == "detailed":
        types_section += f"✅ View {len(passing)} passing files\n\n"
        types_section += "<details>\n<summary>Details</summary>\n\n"
        types_section += "| File | Type Safety Index | Status |\n"
        types_section += "| :--- | :---------------: | :----- |\n"
        for res in sorted(passing, key=lambda x: x.get("type_coverage", 0), reverse=True):
            coverage = res.get("type_coverage", 0)
            types_section += f"| {res['file']} | {coverage:.0f}% | ✅ |\n"
        types_section += "\n</details>\n"
    elif passing and verbosity == "summary":
        types_section += f"*Note: {len(passing)} passing files hidden to reduce noise.*\n"

    return types_section + "\n"


def _generate_file_table_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    verbosity: str = "detailed",
) -> str:
    """
    Creates a breakdown of analysis for every file with collapsible passing files.
    """
    failing = [s for s in stats if s.get("score", 0) < 70]
    passing = [s for s in stats if s.get("score", 0) >= 70]

    section = "### 📂 File Analysis\n\n"

    if failing:
        section += "| File | Score | Issues |\n"
        section += "| :--- | :---: | :--- |\n"
        for res in sorted(failing, key=lambda x: x.get("score", 0)):
            score = res.get("score", 0)
            section += f"| `{res['file']}` | {score} ❌ | {res.get('issues', '')} |\n"
        section += "\n"
    else:
        section += "✅ All files passed analysis!\n\n"

    if passing and verbosity == "detailed":
        section += f"✅ View {len(passing)} passing files\n\n"
        section += "<details>\n<summary>Details</summary>\n\n"
        section += "| File | Score | Issues |\n"
        section += "| :--- | :---: | :--- |\n"
        for res in sorted(passing, key=lambda x: x.get("score", 0), reverse=True):
            score = res.get("score", 0)
            section += f"| {res['file']} | {score} ✅ | {res.get('issues', '')} |\n"
        section += "\n</details>\n"

    return section


def generate_markdown_report(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    final_score: float,
    path: str,
    profile: Dict[str, Any],
    project_issues: Optional[List[str]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
    report_style: str = "actionable",
) -> str:
    """
    Orchestrates report generation by mapping style to internal verbosity.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.copy()

    # RESOLUTION: Map report_style to internal verbosity logic
    style_map = {"full": "detailed", "actionable": "summary", "collapsed": "quiet"}
    verbosity = style_map.get(report_style, "summary")

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

    report += "## 1. Agent Cognitive Load (ACL)\n*Formula: ACL = Complexity + (LOC / 20)*\n\n"
    
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