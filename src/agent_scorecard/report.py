import os
from . import analyzer

def generate_markdown_report(stats, final_score, path, profile, project_issues=None):
    """Generates a Markdown report from the collected statistics."""

    # Normalize stats
    if isinstance(stats, list):
        file_stats = stats
        dependency_stats = None
        directory_stats = None
    else:
        file_stats = stats.get("files", [])
        dependency_stats = stats.get("dependencies")
        directory_stats = stats.get("directories")

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
    top_complexity = sorted(file_stats, key=lambda x: x['complexity'], reverse=True)[:3]
    top_loc = sorted(file_stats, key=lambda x: x['loc'], reverse=True)[:3]
    top_types = sorted(file_stats, key=lambda x: x['type_coverage'])[:3]

    # Find top ACL offenders
    # In Score mode (list), we have 'acl_violations' list in file dict.
    # In Advisor mode (dict), we have 'functions' list in file dict.

    # Helper to get max ACL per file
    def get_max_acl(f_stat):
        if 'acl_violations' in f_stat:
            return max((v['acl'] for v in f_stat['acl_violations']), default=0)
        elif 'functions' in f_stat:
            return max((f['acl'] for f in f_stat['functions']), default=0)
        return 0

    acl_offenders = [s for s in file_stats if get_max_acl(s) > 15]
    acl_offenders.sort(key=get_max_acl, reverse=True)
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
            targets += f"| High ACL         | {s['file']}      | {get_max_acl(s):.1f}      |\n"

    # --- 3. Agent Prompts ---
    prompts = "\n## 🤖 Agent Prompts\n\n"
    unique_files = {s['file'] for s in top_complexity + top_loc + top_types + top_acl}

    for file_path in unique_files:
        prompts += f"### File: `{file_path}`\n"
        file_s = next(s for s in file_stats if s['file'] == file_path)

        if file_s['complexity'] > profile['max_complexity']:
             prompts += f"- **Complexity**: Score is {file_s['complexity']:.1f}. "
             prompts += f"Prompt: 'Refactor `{file_path}` to reduce cyclomatic complexity below {profile['max_complexity']}. Focus on splitting large functions.'\n"

        if file_s['loc'] > profile['max_loc']:
             prompts += f"- **Length**: LOC is {file_s['loc']}. "
             prompts += f"Prompt: 'Reduce the lines of code in `{file_path}` below {profile['max_loc']}. Consider moving helper functions to other modules.'\n"

        if file_s['type_coverage'] < profile['min_type_coverage']:
             prompts += f"- **Typing**: Coverage is {file_s['type_coverage']:.0f}%. "
             prompts += f"Prompt: 'Increase type hint coverage in `{file_path}` to over {profile['min_type_coverage']}%. Ensure all function arguments and return values are typed.'\n"

        # Add ACL prompts
        high_acl_funcs = []
        if 'acl_violations' in file_s:
            high_acl_funcs = file_s['acl_violations']
        elif 'functions' in file_s:
            high_acl_funcs = [f for f in file_s['functions'] if f['acl'] > 15]

        for func in high_acl_funcs:
             prompts += f"- **ACL**: Function `{func['name']}` has ACL {func['acl']:.1f} (High Cognitive Load). "
             prompts += f"Prompt: 'Refactor function `{func['name']}` in `{file_path}` to reduce complexity and length. ACL {func['acl']:.1f} > 15.'\n"

        prompts += "\n"

    # --- 4. Documentation Health ---
    docs = "## 📚 Documentation Health\n\n"
    missing_docs = analyzer.scan_project_docs(path, ["agents.md"])
    if not missing_docs:
        docs += "✅ `agents.md` found.\n"
    else:
        docs += "❌ `agents.md` not found. Recommended Action: Create an `agents.md` to provide context for AI agents.\n"

    advisor_section = ""
    # --- 5. Advisor Mode Sections (Unified) ---
    # In Advisor Mode (dict stats), we have detailed graphs and entropy.
    # In Score Mode (list stats), we might have project_issues, but not detailed graphs unless we regenerate them or trust project_issues summary.
    # But for "Advisor Mode Analysis", we rely on the extended stats.

    # We display Advisor Section if we have the extended stats OR if we found ACL issues in Score mode.
    # But the prompt specifically asked for Advisor Mode sections (ACL, Dependencies, Context).

    advisor_section += "\n# 🧠 Advisor Mode Analysis\n\n"

    # 5.1 Agent Cognitive Load
    advisor_section += "## Agent Cognitive Load (ACL)\n"
    advisor_section += "Functions with ACL > 15 are considered 'Hallucination Zones'.\n\n"

    high_acl_entries = []
    for f_stat in file_stats:
        if 'acl_violations' in f_stat:
            for v in f_stat['acl_violations']:
                high_acl_entries.append((f_stat['file'], v))
        elif 'functions' in f_stat:
            for f in f_stat['functions']:
                if f['acl'] > 15:
                    high_acl_entries.append((f_stat['file'], f))

    if high_acl_entries:
        advisor_section += "| File | Function | ACL | Complexity | LOC |\n"
        advisor_section += "|---|---|---|---|---|\n"
        # Sort by ACL
        high_acl_entries.sort(key=lambda x: x[1]['acl'], reverse=True)
        for fpath, func in high_acl_entries[:10]:
             # Complexity/LOC might be in func dict depending on source
             comp = func.get('complexity', 0)
             loc = func.get('loc', 0)
             advisor_section += f"| {fpath} | {func['name']} | {func['acl']:.1f} | {comp:.1f} | {loc} |\n"
    else:
        advisor_section += "✅ No functions exceed the ACL threshold.\n"
    advisor_section += "\n"

    # 5.2 Dependency Entanglement
    if dependency_stats:
        advisor_section += "## Dependency Entanglement\n"

        # Circular Dependencies
        cycles = dependency_stats.get("cycles", [])
        advisor_section += "### Circular Dependencies\n"
        if cycles:
            advisor_section += "⚠ **Circular dependencies detected!** These cause infinite recursion in agent planning.\n\n"
            for cycle in cycles:
                cycle_str = " -> ".join(cycle) + " -> " + cycle[0]
                advisor_section += f"- `{cycle_str}`\n"
        else:
             advisor_section += "✅ No circular dependencies detected.\n"
        advisor_section += "\n"

        # God Modules
        god_modules = dependency_stats.get("god_modules", {})
        advisor_section += "### God Modules\n"
        if god_modules:
            advisor_section += "⚠ **God Modules detected!** (Inbound imports > 50). These overload context.\n\n"
            for mod, count in god_modules.items():
                advisor_section += f"- `{mod}`: {count} inbound imports\n"
        else:
            advisor_section += "✅ No God Modules detected.\n"
        advisor_section += "\n"
    elif project_issues and any("Circular Dependencies" in i or "God Modules" in i for i in project_issues):
         # Fallback if we only have summary issues
         advisor_section += "## Dependency Entanglement\n"
         for issue in project_issues:
             if "Circular Dependencies" in issue or "God Modules" in issue:
                 advisor_section += f"- {issue}\n"
         advisor_section += "\n"


    # 5.3 Context Economics
    advisor_section += "## Context Economics\n"

    # Token Budget
    high_token_files = [f for f in file_stats if f.get("tokens", 0) > 32000]

    advisor_section += "### Token Budget (> 32k tokens)\n"
    if high_token_files:
         advisor_section += "⚠ **Files exceeding token budget:**\n\n"
         for f in high_token_files:
             advisor_section += f"- `{f['file']}`: {f['tokens']} tokens\n"
    else:
         # Only report success if we actually counted tokens (which happens in Advisor mode)
         if any("tokens" in f for f in file_stats):
            advisor_section += "✅ All files are within token budget.\n"
         else:
            advisor_section += "ℹ Token analysis not available in Score Mode (use `advise` command).\n"
    advisor_section += "\n"

    # Directory Entropy
    if directory_stats:
         # directory_stats is list of dicts {path, file_count}
         high_entropy_dirs = [d for d in directory_stats if d["file_count"] > 50] # Match Beta threshold
         advisor_section += "### Directory Entropy\n"
         if high_entropy_dirs:
              advisor_section += "⚠ **Directories with too many files (> 50):**\n\n"
              for d in high_entropy_dirs:
                   advisor_section += f"- `{d['path']}`: {d['file_count']} files\n"
         else:
              advisor_section += "✅ Directory structure looks good.\n"
    elif project_issues and any("Directory Entropy" in i for i in project_issues):
         advisor_section += "### Directory Entropy\n"
         for issue in project_issues:
             if "Directory Entropy" in issue:
                 advisor_section += f"- {issue}\n"

    return summary + targets + prompts + docs + advisor_section
