import os
from . import analyzer

def generate_markdown_report(stats, final_score, path, profile, project_issues=None):
    """Generates a Markdown report from the collected statistics."""

    # --- 1. Executive Summary ---
    summary = f"# Agent Scorecard Report\n\n"
    summary += f"**Overall Score: {final_score:.1f}/100** - {'PASS' if final_score >= 70 else 'FAIL'}\n\n"

    if project_issues:
        summary += "### ⚠ Project Issues\n"
        for issue in project_issues:
            summary += f"- {issue}\n"
        summary += "\n"

    # --- 2. Refactoring Targets ---
    targets = "## 🎯 Top Refactoring Targets\n\n"

    # Sort files by offender categories
    top_complexity = sorted(stats, key=lambda x: x['complexity'], reverse=True)[:3]
    top_loc = sorted(stats, key=lambda x: x['loc'], reverse=True)[:3]
    top_types = sorted(stats, key=lambda x: x['type_coverage'])[:3]

    # Find top ACL offenders (files with highest max ACL or count?)
    # Let's say files with any ACL violation
    acl_offenders = [s for s in stats if s.get('acl_violations')]
    # Sort by max ACL in the file
    acl_offenders.sort(key=lambda x: max((f['acl'] for f in x['acl_violations']), default=0), reverse=True)
    top_acl = acl_offenders[:3]

    targets += "| Category         | File Path        | Value      |\n"
    targets += "|------------------|------------------|------------|\n"

    if top_complexity:
        for s in top_complexity:
            targets += f"| Complexity       | {s['file']}      | {s['complexity']:.1f}      |\n"
    if top_loc:
        for s in top_loc:
            targets += f"| Lines of Code    | {s['file']}      | {s['loc']}        |\n"
    if top_types:
        for s in top_types:
            targets += f"| Type Coverage    | {s['file']}      | {s['type_coverage']:.0f}%      |\n"
    if top_acl:
        for s in top_acl:
            max_acl = max(f['acl'] for f in s['acl_violations'])
            targets += f"| High ACL         | {s['file']}      | {max_acl:.1f}      |\n"

    # --- 3. Agent Prompts ---
    prompts = "\n## 🤖 Agent Prompts\n\n"
    unique_files = {s['file'] for s in top_complexity + top_loc + top_types + top_acl}

    for file_path in unique_files:
        prompts += f"### File: `{file_path}`\n"
        file_stats = next(s for s in stats if s['file'] == file_path)

        if file_stats['complexity'] > profile['max_complexity']:
             prompts += f"- **Complexity**: Score is {file_stats['complexity']:.1f}. "
             prompts += f"Prompt: 'Refactor `{file_path}` to reduce cyclomatic complexity below {profile['max_complexity']}. Focus on splitting large functions.'\n"

        if file_stats['loc'] > profile['max_loc']:
             prompts += f"- **Length**: LOC is {file_stats['loc']}. "
             prompts += f"Prompt: 'Reduce the lines of code in `{file_path}` below {profile['max_loc']}. Consider moving helper functions to other modules.'\n"

        if file_stats['type_coverage'] < profile['min_type_coverage']:
             prompts += f"- **Typing**: Coverage is {file_stats['type_coverage']:.0f}%. "
             prompts += f"Prompt: 'Increase type hint coverage in `{file_path}` to over {profile['min_type_coverage']}%. Ensure all function arguments and return values are typed.'\n"

        if file_stats.get('acl_violations'):
             for violation in file_stats['acl_violations']:
                 prompts += f"- **ACL**: Function `{violation['name']}` has ACL {violation['acl']:.1f} (High Cognitive Load). "
                 prompts += f"Prompt: 'Refactor function `{violation['name']}` in `{file_path}` to reduce complexity and length. ACL {violation['acl']:.1f} > 15.'\n"

        prompts += "\n"

    # --- 4. Documentation Health ---
    docs = "## 📚 Documentation Health\n\n"
    missing_docs = analyzer.scan_project_docs(path, ["agents.md"])
    if not missing_docs:
        docs += "✅ `agents.md` found.\n"
    else:
        docs += "❌ `agents.md` not found. Recommended Action: Create an `agents.md` to provide context for AI agents.\n"

    return summary + targets + prompts + docs
