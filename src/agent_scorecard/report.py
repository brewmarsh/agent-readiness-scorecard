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

def generate_advisor_report(stats, dependency_stats, entropy_stats, cycles):
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
