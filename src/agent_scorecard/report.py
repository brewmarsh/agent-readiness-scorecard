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
    profile_desc = profile.get("description", "Generic").split(".")[0]
    summary += f"**Target Agent Profile:** {profile_desc}\n"
    status_str = "PASS" if final_score >= 70 else "FAIL"
    summary += f"**Overall Score: {final_score:.1f}/100** - {status_str}\n\n"

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
    Analyzes and reports on units with high Agent Cognitive Load using AST-depth weights.
    """
    acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
    acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])

    targets = "## 🎯 Top Refactoring Targets (Agent Cognitive Load (ACL))\n\n"
    # RESOLUTION: Adopted the high-fidelity formula focusing on nesting depth
    targets += f"ACL = (Depth * 2) + (Complexity * 1.5) + (LOC / 50). Target: ACL <= {acl_yellow}.\n\n"

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
    """
    type_safety_threshold = thresholds.get(
        "type_safety", DEFAULT_THRESHOLDS["type_safety"]
    )

    types_section = "## 🛡️ Type Safety Index\n\n"
    types_section += (
        f"Target: >{type_safety_threshold}% of functions "
        "must have explicit type signatures.\n\n"
    )

    sorted_types = sorted(stats, key=lambda x: x.get("type_coverage", 0))
    table_rows = []
    for res in sorted_types:
        coverage = res.get("type_coverage", 0)
        if verbosity == "summary" and coverage >= type_safety_threshold:
            continue
        status = "✅" if coverage >= type_safety_threshold else "❌"
        table_rows.append(f"| {res['file']} | {coverage:.0f}% | {status} |")

    if not table_rows:
        return types_section + "✅ All files meet type safety requirements.\n\n"

    types_section += "| File | Type Safety Index | Status |\n"
    types_section += "| :--- | :---------------: | :----- |\n"
    types_section += "\n".join(table_rows)

    return types_section + "\n\n"


def _generate_file_table_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    verbosity: str = "detailed",
) -> str:
    """
    Creates a breakdown of analysis for every file grouped by language.
    """
    if verbosity == "summary":
        title = "### 📂 Failing File Analysis"
    else:
        title = "### 📂 Full File Analysis"

    # Group files by language
    grouped: Dict[str, List[Any]] = {}
    for res in stats:
        lang = res.get("language", "Unknown")
        if lang not in grouped:
            grouped[lang] = []
        grouped[lang].append(cast(Dict[str, Any], res))

    sections = []
    for lang in sorted(grouped.keys()):
        lang_files = grouped[lang]
        failing = [f for f in lang_files if f.get("score", 0) < 70]
        passing = [f for f in lang_files if f.get("score", 0) >= 70]

        if not failing and verbosity == "summary":
            continue

        lang_section = [f"#### {lang}"]

        if failing:
            lang_section.append("| File | Score | Issues |")
            lang_section.append("| :--- | :---: | :--- |")
            for res in failing:
                lang_section.append(
                    f"| {res['file']} | {res['score']} ❌ | {res.get('issues', '')} |"
                )

        if passing and verbosity == "detailed":
            lang_section.append("\n<details>")
            lang_section.append(
                f"<summary>View {len(passing)} Passing {lang} Files</summary>\n"
            )
            lang_section.append("| File | Score | Issues |")
            lang_section.append("| :--- | :---: | :--- |")
            for res in passing:
                lang_section.append(f"| {res['file']} | {res['score']} ✅ | |")
            lang_section.append("\n</details>\n")
        elif passing and failing and verbosity == "summary":
            lang_section.append(f"\n*Plus {len(passing)} passing files hidden.*\n")

        sections.append("\n".join(lang_section))

    if not sections and verbosity == "summary":
        return "### 📂 File Analysis\n\n✅ All files passed!\n"

    return title + "\n\n" + "\n\n".join(sections)


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
    Orchestrates the Markdown report generation using customizable styles.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.copy()

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

    # RESOLUTION: Updated Advisor report to reflect high-fidelity ACL formula
    report += "## 1. Agent Cognitive Load (ACL)\n*Formula: ACL = (Depth * 2) + (Complexity * 1.5) + (LOC / 50)*\n\n"

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
