"""Block dangerous Agent Zero tools for the Avender sales agent (SRS REQ-3.2.2).

The avender_sales profile is a heavily restricted sales bot.
It must NEVER be allowed to access OS-level tools like terminal, write_file,
read_file, code_execution, etc. — even if a prompt injection attack tricks
the LLM into calling them.

This extension fires BEFORE any tool execution and raises a HandledException
if the tool is not in the Avender allowlist, which cleanly aborts the tool
call and feeds the error message back into the cognitive loop.
"""

from typing import Any

from helpers.extension import Extension
from helpers.errors import HandledException
from helpers.print_style import PrintStyle

from usr.plugins.avender.helpers.config import get_setting

# Base tools allowed for everyone
BASE_TOOLS = {
    "save_interaction_record",
    "process_location",
    "handoff_to_human",
    "call_subordinate",
    "response",
}

# Tools specific to archetypes
ARCHETYPE_TOOLS = {
    "restaurant": {"search_catalog", "calculate_total"},
    "retail": {"search_catalog", "calculate_total"},
    "groceries": {"search_catalog", "calculate_total"},
    "beauty": {"search_catalog", "calculate_total"},
    "tech": {"search_catalog", "calculate_total"},
    "services": {"search_catalog", "calculate_total"},
    "doctor": {"search_catalog"},
    "pharmacy": {"search_catalog", "calculate_total"},
    "hardware": {"search_catalog", "calculate_total"},
    "liquor": {"search_catalog", "calculate_total"},
    "cbd": {"search_catalog", "calculate_total"},
    "medical": {"search_catalog"},  # backward-compatible alias
    "real_estate": {"search_catalog"}, # properties catalog
    "subscriptions": {"search_catalog"},
}

AVENDER_AGENT_PROFILE = "avender_sales"

class AvenderToolSandbox(Extension):
    """Reject tool calls not in the Avender allowlist."""

    async def execute(
        self,
        tool_args: dict[str, Any] | None = None,
        tool_name: str = "",
        **kwargs,
    ):
        if not self.agent:
            return

        # Only enforce for the avender_sales agent profile
        agent_profile = getattr(self.agent.config, "agent_profile", "")
        if agent_profile != AVENDER_AGENT_PROFILE:
            return

        archetype = get_setting("archetype", "retail")
        
        # Build dynamic allowlist
        allowed_tools = set(BASE_TOOLS)
        allowed_tools.update(ARCHETYPE_TOOLS.get(archetype, set()))

        # Admin contexts are flagged via the WhatsApp admin backdoor session.
        # update_catalog_item is globally allowed — the LLM is only instructed to use it in Admin mode.
        allowed_tools.add("update_catalog_item")

        if tool_name and tool_name not in allowed_tools:
            PrintStyle.error(
                f"Avender Sandbox: BLOCKED tool '{tool_name}' — "
                f"not in allowlist for archetype '{archetype}'"
            )
            raise HandledException(
                f"Tool '{tool_name}' is not available for the '{archetype}' archetype. "
                f"Available tools: {', '.join(sorted(allowed_tools))}."
            )
