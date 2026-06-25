from typing import Optional
from .types import EnvironmentHealth

# ... Helper functions _get_status_message, _generate_summary_section, _flatten_functions remain as implemented ...


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
    section += f"| AGENTS.md | {'✅ PASS' if health['agents_md'] else '❌ FAIL'} |\n"
    section += f"| Lock File | {'✅ PASS' if health['lock_file'] else '❌ FAIL'} |\n"

    # RESOLUTION: Unified BAML Detection into the broader Agentic Ecosystem view
    ecosystem = health.get("agentic_ecosystem")

    # 1. BAML / Framework Detection (+10 Bonus)
    if health.get("baml_detected") or (
        ecosystem and ecosystem.get("has_agent_frameworks")
    ):
        frameworks = ecosystem.get("found_frameworks", []) if ecosystem else []
        if health.get("baml_detected") and "baml" not in frameworks:
            frameworks.append("baml")

        frameworks_str = ", ".join(frameworks)
        section += f"| Agent Frameworks | 🤖 [PASS] ({frameworks_str}) (+10) |\n"
    else:
        section += "| Agent Frameworks | 🟡 None |\n"

    # 2. Context Steering (+5 Bonus)
    if ecosystem and ecosystem.get("has_context_files"):
        files_str = ", ".join(ecosystem.get("found_files", []))
        section += f"| Context Steering | 📜 [PASS] ({files_str}) (+5) |\n"
    else:
        section += "| Context Steering | 🟡 None |\n"

    return section + "\n"


# ... Orchestration logic for generate_markdown_report and generate_advisor_report remain as implemented ...
