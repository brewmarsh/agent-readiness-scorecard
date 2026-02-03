import os
from . import analyzer

def generate_markdown_report(stats, final_score, path, profile):
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

    # --- 2. Refactoring Targets ---
    targets = "## 🎯 Top Refactoring Targets\n\n"

    # Sort files by offender categories
    top_complexity = sorted(file_stats, key=lambda x: x['complexity'], reverse=True)[:3]
    top_loc = sorted(file_stats, key=lambda x: x['loc'], reverse=True)[:3]
    top_types = sorted(file_stats, key=lambda x: x['type_coverage'])[:3]

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

    # --- 3. Agent Prompts ---
    prompts = "\n## 🤖 Agent Prompts\n\n"
    unique_files = {s['file'] for s in top_complexity + top_loc + top_types}

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
        prompts += "\n"

    # --- 4. Documentation Health ---
    docs = "## 📚 Documentation Health\n\n"
    missing_docs = analyzer.scan_project_docs(path, ["agents.md"])
    if not missing_docs:
        docs += "✅ `agents.md` found.\n"
    else:
        docs += "❌ `agents.md` not found. Recommended Action: Create an `agents.md` to provide context for AI agents.\n"

    advisor_section = ""
    # --- 5. Advisor Mode Sections ---
    # Check if we have extended stats (tokens, functions, dependencies)
    has_advisor_stats = dependency_stats is not None or any("tokens" in f for f in file_stats)

    if has_advisor_stats:
        advisor_section += "\n# 🧠 Advisor Mode Analysis\n\n"

        # 5.1 Agent Cognitive Load
        # We need to find functions with ACL > 15
        high_acl_funcs = []
        for f_stat in file_stats:
            if "functions" in f_stat:
                for func in f_stat["functions"]:
                    if func.get("acl", 0) > 15:
                         high_acl_funcs.append((f_stat["file"], func))

        advisor_section += "## Agent Cognitive Load (ACL)\n"
        advisor_section += "Functions with ACL > 15 are considered 'Hallucination Zones'.\n\n"
        if high_acl_funcs:
            advisor_section += "| File | Function | ACL | Complexity | LOC |\n"
            advisor_section += "|---|---|---|---|---|\n"
            for fpath, func in sorted(high_acl_funcs, key=lambda x: x[1]['acl'], reverse=True)[:10]:
                 advisor_section += f"| {fpath} | {func['name']} | {func['acl']:.1f} | {func['complexity']:.1f} | {func['loc']} |\n"
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
             advisor_section += "✅ All files are within token budget.\n"
        advisor_section += "\n"

        # Directory Entropy
        if directory_stats:
             high_entropy_dirs = [d for d in directory_stats if d["file_count"] > 30]
             advisor_section += "### Directory Entropy\n"
             if high_entropy_dirs:
                  advisor_section += "⚠ **Directories with too many files (> 30):**\n\n"
                  for d in high_entropy_dirs:
                       advisor_section += f"- `{d['path']}`: {d['file_count']} files\n"
             else:
                  advisor_section += "✅ Directory structure looks good.\n"

    return summary + targets + prompts + docs + advisor_section
