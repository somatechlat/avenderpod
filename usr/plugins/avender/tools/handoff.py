"""
handoff_to_human tool — Native WhatsApp implementation via Baileys bridge.

When triggered, this tool:
1. Sets a flag in context.data so the WA polling loop STOPS auto-replying.
2. Sends a final message to the customer explaining a human will assist.
3. Logs the handoff event in the interaction_record table.
4. The Tenant Admin Dashboard detects the flag and highlights the conversation
   for human intervention.
"""

import json

from helpers.tool import Tool, Response
from helpers.print_style import PrintStyle
from usr.plugins.avender.helpers.db import get_connection

# Context key that signals the WA reply extension to pause auto-replies
HANDOFF_FLAG = "avender_human_handoff"


class HandoffToHuman(Tool):
    name = "handoff_to_human"
    description = (
        "Pauses the AI agent and requests human intervention. Use this ONLY when "
        "the customer explicitly asks to speak to a human, or when the issue cannot "
        "be resolved by the AI. The business owner will be notified in the dashboard."
    )
    parameters = {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Brief reason for requesting human intervention.",
            }
        },
        "required": ["reason"],
    }

    async def execute(self, reason: str, **kwargs):
        context = self.agent.context

        # 1. Set the handoff flag — WA reply extension checks this to suppress AI replies
        context.data[HANDOFF_FLAG] = True
        context.data["avender_handoff_reason"] = reason

        # 2. Log handoff event to DB for the dashboard to surface
        sender_wa_id = context.data.get("wa_sender_number", "unknown")
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO interaction_record (customer_wa_id, archetype, status, payload) VALUES (?, ?, ?, ?)",
                (
                    sender_wa_id,
                    "human_handoff",
                    "pending",
                    json.dumps({"reason": reason, "context_id": context.id}),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            PrintStyle.error(f"Avender handoff: failed to log to DB: {e}")

        PrintStyle.success(
            f"Avender: Human handoff activated for {sender_wa_id}. Reason: {reason}"
        )

        return Response(
            message=(
                f"Human handoff activated. Reason: {reason}. "
                "The business owner has been notified in the dashboard. "
                "Tell the customer: 'Un agente humano te atenderá pronto. "
                "Por favor espera unos minutos.' Then STOP responding."
            ),
            break_loop=True,
        )
