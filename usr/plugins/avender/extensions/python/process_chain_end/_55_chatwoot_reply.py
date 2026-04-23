"""Route Agent Zero responses back through Chatwoot for WhatsApp delivery.

This extension fires after the cognitive loop completes (process_chain_end).
It extracts the agent's final response from the log and sends it as an
outgoing message via the Chatwoot Conversations API.

Only activates for contexts that were created by the Avender webhook handler
(identified by the presence of 'cw_conversation_id' in context.data).
"""

import asyncio

import requests as http_requests

from agent import AgentContext, LoopData
from helpers.extension import Extension
from helpers.plugins import get_plugin_config
from helpers.print_style import PrintStyle


class AvenderChatwootReply(Extension):
    """Send agent replies back to the customer via Chatwoot."""

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent or self.agent.number != 0:
            return

        context = self.agent.context
        conversation_id = context.data.get("cw_conversation_id")
        if not conversation_id:
            # Not an Avender session — skip
            return

        response_text = _extract_last_response(context)
        if not response_text:
            return

        # Fire-and-forget so we don't block the cognitive loop
        asyncio.create_task(
            _send_chatwoot_reply(conversation_id, response_text)
        )


async def _send_chatwoot_reply(conversation_id: str, message: str) -> None:
    """POST the agent response to Chatwoot as an outgoing message."""
    config = get_plugin_config("avender") or {}
    cw_url = config.get("chatwoot_url", "")
    cw_token = config.get("chatwoot_api_token", "")

    if not cw_url or not cw_token:
        PrintStyle.error(
            "Avender reply: chatwoot_url or chatwoot_api_token not configured."
        )
        return

    account_id = config.get("chatwoot_account_id", "1")
    endpoint = (
        f"{cw_url.rstrip('/')}/api/v1/accounts/{account_id}/conversations"
        f"/{conversation_id}/messages"
    )
    try:
        resp = http_requests.post(
            endpoint,
            json={"content": message, "message_type": "outgoing"},
            headers={"api_access_token": cw_token},
            timeout=15,
        )
        resp.raise_for_status()
        PrintStyle.success(
            f"Avender: Reply delivered to conversation {conversation_id} "
            f"({len(message)} chars)"
        )
    except Exception as e:
        PrintStyle.error(f"Avender: Failed to deliver reply via Chatwoot: {e}")


def _extract_last_response(context: AgentContext) -> str:
    """Extract the most recent 'response' log entry from the agent context."""
    with context.log._lock:
        logs = list(context.log.logs)
    if not logs:
        return ""
    for item in reversed(logs):
        if item.type == "response":
            return item.content or ""
    return ""
