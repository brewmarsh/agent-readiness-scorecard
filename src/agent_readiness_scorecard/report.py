from typing import List, Dict, Any, Optional, Union, cast, Tuple
from .constants import DEFAULT_THRESHOLDS
from .types import FileAnalysisResult, AdvisorFileResult, EnvironmentHealth
from .remediation import generate_prompts_section, generate_recommendations_report

__all__ = ["generate_recommendations_report", "generate_prompts_section"]


def _get_status_message(final_score: float) -> str:
    """
    Returns the status message based on final score.
    """
    if final_score >= 70:
        return "✅ **Status: PASSED** - This codebase is Agent-Ready.\n\n"
    return "❌ **Status: FAILED** - This codebase needs improvement for AI Agents.\n\n"


def _generate_summary_section(
    final_score: float,
    profile: Dict[str, Any],
    project_issues: Optional[List[str]],
    version: str = "0.0.0",
) -> str:
    """
    Creates the executive summary section of the report.
    """
    profile_desc = profile.get("description", "Generic").split(".")[0]
    status_str = "PASS" if final_score >= 70 else "FAIL"

    summary = [
        f"# Agent Readiness Scorecard Report v{version}\n",
        f"**Target Agent Profile:** {profile_desc}",
        f"**Overall Score: {final_score:.1f}/100** - {status_str}\n",
        _get_status_message(final_score),
    ]

    if project_issues:
        summary.append("### ⚠️ Project Issues")
        summary.extend([f"- {issue}" for issue in project_issues])
        summary.append("")

    return "\n".join(summary)


def _flatten_functions(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Flattens functions from file results into a single list.
    """
    all_functions = []
    for f_res in stats:
        metrics = f_res.get("function_metrics", [])
        for m in metrics:
            all_functions.append({**m, "file": f_res["file"]})
    return all_functions


def _get_sorted_high_acl_functions(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    acl_yellow: float,
    sort_by: str = "acl",
    top_limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Flattens, filters and sorts functions by ACL.
    """
    all_functions = _flatten_functions(stats)

    high_acl_functions = [
        fn for fn in all_functions if cast(float, fn.get("acl", 0)) > acl_yellow
    ]

    sort_key = sort_by if sort_by in ["acl", "loc", "complexity"] else "acl"
    sorted_funcs = sorted(
        high_acl_functions, key=lambda x: x.get(sort_key, 0), reverse=True
    )

    if top_limit is not None:
        return sorted_funcs[:top_limit]
    return sorted_funcs


def _generate_acl_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    thresholds: Dict[str, Any],
    sort_by: str = "acl",
    top_limit: Optional[int] = None,
) -> str:
    """
    Analyzes and reports on units with high Agent Cognitive Load using AST-depth weights.
    """
    acl_yellow = thresholds.get("acl_yellow", DEFAULT_THRESHOLDS["acl_yellow"])
    acl_red = thresholds.get("acl_red", DEFAULT_THRESHOLDS["acl_red"])

    header = "## 🎯 Top Refactoring Targets (Agent Cognitive Load (ACL))\n\n"
    header += f"ACL = (Depth * 2) + (Complexity * 1.5) + (LOC / 50). Target: ACL <= {acl_yellow}.\n\n"

    sorted_funcs = _get_sorted_high_acl_functions(stats, acl_yellow, sort_by, top_limit)

    if not sorted_funcs:
        return header + f"✅ All functions meet the Agent Cognitive Load (ACL) target of <= {acl_yellow}.\n\n"

    rows = ["| Function | File | ACL | Status |", "|----------|------|-----|--------|"]
    for fn in sorted_funcs:
        acl_val = cast(float, fn.get("acl", 0))
        status = "🔴 Red" if acl_val > acl_red else "🟡 Yellow"
        rows.append(f"| `{fn['name']}` | `{fn['file']}` | {acl_val:.1f} | {status} |")

    return header + "\n".join(rows) + "\n\n"


def _generate_type_safety_rows(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    threshold: float,
    verbosity: str,
) -> List[str]:
    """
    Generates table rows for type safety.
    """
    sorted_types = sorted(stats, key=lambda x: x.get("type_coverage", 0))
    table_rows = []
    for res in sorted_types:
        coverage = res.get("type_coverage", 0)
        if verbosity == "summary" and coverage >= threshold:
            continue
        status = "✅" if coverage >= threshold else "❌"
        table_rows.append(f"| {res['file']} | {coverage:.0f}% | {status} |")
    return table_rows


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

    header = "## 🛡️ Type Safety Index\n\n"
    header += (
        f"Target: >{type_safety_threshold}% of functions "
        "must have explicit type signatures.\n\n"
    )

    table_rows = _generate_type_safety_rows(stats, type_safety_threshold, verbosity)

    if not table_rows:
        return header + "✅ All files meet type safety requirements.\n\n"

    table_header = ["| File | Type Safety Index | Status |", "| :--- | :---------------: | :----- |"]
    return header + "\n".join(table_header + table_rows) + "\n\n"


def _group_files_by_language(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Groups analysis results by language.
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for res in stats:
        lang = res.get("language", "Unknown")
        if lang not in grouped:
            grouped[lang] = []
        grouped[lang].append(cast(Dict[str, Any], res))
    return grouped


def _generate_passing_details_detailed(passing: List[Dict[str, Any]], lang: str) -> str:
    """
    Generates detailed list of passing files.
    """
    rows = [
        "\n<details>",
        f"<summary>View {len(passing)} Passing {lang} Files</summary>\n",
        "| File | Score | Issues |",
        "| :--- | :---: | :--- |",
    ]
    for res in passing:
        rows.append(f"| {res['file']} | {res['score']} ✅ | |")
    rows.append("\n</details>\n")
    return "\n".join(rows)


def _generate_passing_details(
    passing: List[Dict[str, Any]], lang: str, verbosity: str, has_failing: bool
) -> str:
    """
    Generates details for passing files.
    """
    if verbosity == "detailed":
        return _generate_passing_details_detailed(passing, lang)

    if has_failing and verbosity == "summary":
        return f"\n*Plus {len(passing)} passing files hidden.*\n"

    return ""


def _generate_failing_rows(failing: List[Dict[str, Any]]) -> List[str]:
    """
    Generates markdown table rows for failing files.
    """
    rows = ["| File | Score | Issues |", "| :--- | :---: | :--- |"]
    for res in failing:
        rows.append(f"| {res['file']} | {res['score']} ❌ | {res.get('issues', '')} |")
    return rows


def _generate_language_section(
    lang: str, lang_files: List[Dict[str, Any]], verbosity: str
) -> Optional[str]:
    """
    Generates a section for a specific language.
    """
    failing = [f for f in lang_files if f.get("score", 0) < 70]
    passing = [f for f in lang_files if f.get("score", 0) >= 70]

    if not failing and verbosity == "summary":
        return None

    lang_section = [f"#### {lang}"]
    if failing:
        lang_section.extend(_generate_failing_rows(failing))

    if passing:
        lang_section.append(
            _generate_passing_details(passing, lang, verbosity, bool(failing))
        )

    return "\n".join(lang_section)


def _generate_sections_by_language(
    grouped: Dict[str, List[Dict[str, Any]]], verbosity: str
) -> List[str]:
    """
    Generates report sections for each language.
    """
    sections = []
    for lang in sorted(grouped.keys()):
        section = _generate_language_section(lang, grouped[lang], verbosity)
        if section:
            sections.append(section)
    return sections


def _generate_file_table_section(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    verbosity: str = "detailed",
) -> str:
    """
    Creates a breakdown of analysis for every file grouped by language.
    """
    title = (
        "### 📂 Failing File Analysis"
        if verbosity == "summary"
        else "### 📂 Full File Analysis"
    )

    grouped = _group_files_by_language(stats)
    sections = _generate_sections_by_language(grouped, verbosity)

    if not sections and verbosity == "summary":
        return "### 📂 File Analysis\n\n✅ All files passed!\n"

    return title + "\n\n" + "\n\n".join(sections)


def _generate_environment_health_section(
    health: Optional[EnvironmentHealth] = None,
) -> str:
    """
    Creates the environment health section of the report.
    """
    if not health:
        return ""

    section = "## 🏗️ Environment Health\n\n"
    section += "| Check | Status |\n"
    section += "| :--- | :--- |\n"
    section += (
        f"| AGENTS.md | {'✅ PASS' if health['agents_md'] else '❌ FAIL'} |\n"
    )
    section += (
        f"| Linter Config | {'✅ PASS' if health['linter_config'] else '❌ FAIL'} |\n"
    )
    section += (
        f"| Lock File | {'✅ PASS' if health['lock_file'] else '❌ FAIL'} |\n"
    )
    if health.get("baml_detected"):
        section += "| BAML Detection | ✅ [PASS] BAML Structured Outputs Detected (+10) |\n"
    else:
        section += "| BAML Detection | 🟡 NOT FOUND |\n"

    return section + "\n"


def generate_markdown_report(
    stats: Union[List[FileAnalysisResult], List[Dict[str, Any]]],
    final_score: float,
    path: str,
    profile: Dict[str, Any],
    project_issues: Optional[List[str]] = None,
    thresholds: Optional[Dict[str, Any]] = None,
    report_style: str = "actionable",
    version: str = "0.0.0",
    sort_by: str = "acl",
    top_limit: Optional[int] = None,
    environment_health: Optional[EnvironmentHealth] = None,
) -> str:
    """
    Orchestrates the Markdown report generation using customizable styles.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.copy()

    style_map = {"full": "detailed", "actionable": "summary", "collapsed": "quiet"}
    verbosity = style_map.get(report_style, "summary")

    # --- SORTING & LIMITING ---
    summary = _generate_summary_section(final_score, profile, project_issues, version)

    if verbosity == "quiet":
        return summary + "\n---\n*Generated by Agent-Readiness-Scorecard*"

    health_section = _generate_environment_health_section(environment_health)
    targets = _generate_acl_section(stats, thresholds, sort_by, top_limit)
    # --- END SORTING & LIMITING ---
    types_section = _generate_type_safety_section(stats, thresholds, verbosity)
    prompts = generate_prompts_section(stats, thresholds, project_issues)
    table = _generate_file_table_section(stats, verbosity)

    return (
        summary
        + health_section
        + targets
        + types_section
        + prompts
        + "\n"
        + table
        + "\n---\n*Generated by Agent-Readiness-Scorecard*"
    )


def _generate_advisor_acl_section(
    stats: Union[List[AdvisorFileResult], List[Dict[str, Any]]],
) -> str:
    """
    Generates the ACL section of the Advisor Report.
    """
    section = "## 1. Agent Cognitive Load (ACL)\n*Formula: ACL = (Depth * 2) + (Complexity * 1.5) + (LOC / 50)*\n\n"
    high_acl_files = sorted(
        [s for s in stats if s.get("acl", 0) > 15],
        key=lambda x: x.get("acl", 0),
        reverse=True,
    )
    if high_acl_files:
        section += "### 🚨 Hallucination Zones (ACL > 15)\n| File | ACL | Complexity | LOC |\n|---|---|---|---|\n"
        for s in high_acl_files:
            section += f"| `{s['file']}` | **{s.get('acl', 0):.1f}** | {s.get('complexity', 0):.1f} | {s.get('loc', 0)} |\n"
    else:
        section += "✅ No Hallucination Zones detected.\n"
    return section


def _generate_advisor_tokens_section(
    stats: Union[List[AdvisorFileResult], List[Dict[str, Any]]],
) -> str:
    """
    Generates the Context Economics section of the Advisor Report.
    """
    section = "\n## 2. Context Economics\n"
    high_token_files = [f for f in stats if f.get("tokens", 0) > 32000]
    if high_token_files:
        section += "### 🪙 Token Budget (> 32k tokens)\n"
        for f in high_token_files:
            section += f"- `{f['file']}`: {f.get('tokens', 0)} tokens\n"
    else:
        section += "✅ All files within context window limits.\n"
    return section


def _generate_god_modules_table(god_modules: List[Tuple[str, int]]) -> str:
    """
    Generates the god modules table.
    """
    section = "### 🕸 God Modules\n| File | Inbound Refs |\n|---|---|\n"
    for k, v in god_modules:
        section += f"| `{k}` | {v} |\n"
    return section


def _generate_cycles_list(cycles: List[List[str]]) -> str:
    """
    Generates the circular dependencies list.
    """
    section = "### 🔄 Circular Dependencies\n"
    for cycle in cycles:
        section += f"- {' -> '.join(cycle)} -> {cycle[0]}\n"
    return section


def _generate_advisor_dependency_section(
    dependency_stats: Dict[str, int], cycles: List[List[str]]
) -> str:
    """
    Generates the Dependency Entanglement section of the Advisor Report.
    """
    section = "\n## 3. Dependency Entanglement\n"
    god_modules = sorted(
        {k: v for k, v in dependency_stats.items() if v > 50}.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    if god_modules:
        section += _generate_god_modules_table(god_modules)

    if cycles:
        section += _generate_cycles_list(cycles)
    else:
        section += "✅ No Circular Dependencies detected.\n"
    return section


def _generate_crowded_dirs_list(crowded_dirs: Dict[str, int]) -> str:
    """
    Generates the list of crowded directories.
    """
    section = "### 📂 Crowded Directories (> 15 files)\n"
    for p, c in crowded_dirs.items():
        section += f"- `{p}`: {c} files\n"
    return section


def _generate_advisor_entropy_section(entropy_stats: Dict[str, int]) -> str:
    """
    Generates the Directory Entropy section of the Advisor Report.
    """
    if not entropy_stats:
        return ""

    section = "\n## 4. Directory Entropy\n"
    crowded_dirs = {p: c for p, c in entropy_stats.items() if c > 15}
    if crowded_dirs:
        section += _generate_crowded_dirs_list(crowded_dirs)
    else:
        section += "✅ Directory structure is balanced.\n"
    return section


def generate_advisor_report(
    stats: Union[List[AdvisorFileResult], List[Dict[str, Any]]],
    dependency_stats: Dict[str, int],
    entropy_stats: Dict[str, int],
    cycles: List[List[str]],
) -> str:
    """
    Generates the advanced Advisor Report based on Agent Physics.
    """
    report = "# 🧠 Agent Readiness Advisor Report\n\nAnalysis based on the **Physics of Agent-Code Interaction**.\n\n"
    report += _generate_advisor_acl_section(stats)
    report += _generate_advisor_tokens_section(stats)
    report += _generate_advisor_dependency_section(dependency_stats, cycles)
    report += _generate_advisor_entropy_section(entropy_stats)
    return report
