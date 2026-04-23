import requests as http_requests

from helpers.tool import Tool, Response
from helpers.plugins import get_plugin_config
from helpers.print_style import PrintStyle


class HandoffToHuman(Tool):
    name = "handoff_to_human"
    description = (
        "Triggers the native Chatwoot human handoff. Use this ONLY when the "
        "customer explicitly asks to speak to a human or if you cannot resolve their issue."
    )
    parameters = {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Reason for handoff."}
        },
        "required": ["reason"],
    }

    async def execute(self, reason: str, **kwargs):
        config = get_plugin_config("avender") or {}
        cw_url = config.get("chatwoot_url", "")
        cw_token = config.get("chatwoot_api_token", "")

        if not cw_url or not cw_token:
            PrintStyle.error("Avender handoff: chatwoot_url or chatwoot_api_token not configured.")
            return Response(
                message="Error: Chatwoot credentials not configured. Cannot perform handoff.",
                break_loop=True,
            )

        # Retrieve the conversation ID stored by the webhook handler
        conversation_id = self.agent.context.data.get("cw_conversation_id")
        if not conversation_id:
            PrintStyle.error("Avender handoff: No conversation ID in context data.")
            return Response(
                message="Error: No active Chatwoot conversation found for this session.",
                break_loop=True,
            )

        # Chatwoot API: Toggle conversation status to 'open' which removes
        # the AgentBot and routes the conversation to a human agent via
        # Chatwoot's native assignment rules (SRS Rec 1).
        account_id = config.get("chatwoot_account_id", "1")
        endpoint = (
            f"{cw_url.rstrip('/')}/api/v1/accounts/{account_id}/conversations"
            f"/{conversation_id}/toggle_status"
        )
        try:
            resp = http_requests.post(
                endpoint,
                json={"status": "open"},
                headers={"api_access_token": cw_token},
                timeout=15,
            )
            resp.raise_for_status()
            PrintStyle.success(
                f"Avender: Handoff successful for conversation {conversation_id}. "
                f"Reason: {reason}"
            )
        except Exception as e:
            PrintStyle.error(f"Avender: Handoff API call failed: {e}")
            return Response(
                message=f"Handoff API error: {e}. Please try again or contact support.",
                break_loop=True,
            )

        return Response(
            message=(
                f"Handoff to human agent completed successfully (Reason: {reason}). "
                "Say goodbye to the customer and stop processing immediately."
            ),
            break_loop=True,
        )
