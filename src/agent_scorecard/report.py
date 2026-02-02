from typing import List, Dict, Any

def generate_report(
    project_score: float,
    file_results: List[Dict[str, Any]],
    missing_docs: List[str],
    profile: Dict[str, Any]
) -> str:
    """Generates a Markdown report with actionable advice."""

    report = [
        "# 🕵️ Agent Scorecard Report",
        f"\n**Final Score:** {project_score:.1f}/100",
        f"**Profile:** {profile.get('description', 'Custom')}",
        "\n## 🚨 Critical Issues",
    ]

    if missing_docs:
        report.append("\n### ❌ Missing Documentation")
        report.append("Agents rely on these files to understand your project context.")
        for doc in missing_docs:
            report.append(f"- `root/{doc}`: Missing.")
        report.append("\n**Fix:** Run `agent-score --fix` to generate these files.")

    # Identify problematic files
    bloated_files = [f for f in file_results if f['loc'] > profile['max_loc']]
    complex_files = [f for f in file_results if f['complexity'] > profile['max_complexity']]
    untyped_files = [f for f in file_results if f['type_coverage'] < profile['min_type_coverage']]

    if bloated_files:
        report.append("\n### 📉 Bloated Files (Too Large)")
        report.append(f"Files larger than {profile['max_loc']} lines confuse agents.")
        for f in bloated_files:
            report.append(f"- `{f['filepath']}`: **{f['loc']} lines**")

    if complex_files:
        report.append("\n### 🌀 Complex Logic")
        report.append(f"Cyclomatic complexity > {profile['max_complexity']} makes reasoning hard.")
        for f in complex_files:
            report.append(f"- `{f['filepath']}`: **{f['complexity']:.1f} avg complexity**")

    if untyped_files:
        report.append("\n### ❓ Missing Type Hints")
        report.append(f"Type coverage < {profile['min_type_coverage']}% leads to hallucinations.")
        for f in untyped_files:
            report.append(f"- `{f['filepath']}`: **{f['type_coverage']:.0f}% covered**")

    if not (missing_docs or bloated_files or complex_files or untyped_files):
        report.append("\n✅ No critical issues found! Your codebase is agent-ready.")

    report.append("\n## 💡 Recommendations")
    report.append("1. **Refactor large files**: Break them into smaller modules.")
    report.append("2. **Add Type Hints**: Use `agent-score --fix` to add TODOs.")
    report.append("3. **Simplify Logic**: Reduce nesting and split complex functions.")

    return "\n".join(report)
