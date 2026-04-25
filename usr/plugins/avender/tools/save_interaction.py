import hashlib
import json

from helpers.tool import Tool, Response
from usr.plugins.avender.helpers.db import get_connection

DEDUP_WINDOW_SECONDS = 30  # SRS Rec 3: prevent double-orders from webhook retries


class SaveInteractionRecord(Tool):
    name = "save_interaction_record"
    description = "Saves an order, booking, or lead profile to the database."
    parameters = {
        "type": "object",
        "properties": {
            "customer_wa_id": {
                "type": "string",
                "description": "WhatsApp number of the customer.",
            },
            "archetype": {
                "type": "string",
                "description": "Type of interaction: 'food_order', 'medical_booking', 'lead'.",
            },
            "payload": {
                "type": "string",
                "description": "JSON string containing all the interaction details (items, total, date, etc).",
            },
        },
        "required": ["customer_wa_id", "archetype", "payload"],
    }

    async def execute(
        self, customer_wa_id: str, archetype: str, payload: str, **kwargs
    ):
        # SRS Rec 3: Idempotency check — reject duplicates within 30-second window
        payload_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM interaction_record "
            "WHERE customer_wa_id = ? AND archetype = ? "
            "AND created_at >= datetime('now', ?)",
            (customer_wa_id, archetype, f"-{DEDUP_WINDOW_SECONDS} seconds"),
        )
        if cursor.fetchone():
            conn.close()
            return Response(
                message="This interaction was already saved within the last 30 seconds (duplicate prevented).",
                break_loop=False,
            )

        cursor.execute(
            "INSERT INTO interaction_record (customer_wa_id, archetype, status, payload) VALUES (?, ?, ?, ?)",
            (customer_wa_id, archetype, "completed", payload),
        )
        conn.commit()
        conn.close()
        return Response(
            message="Interaction successfully saved to the database. You may now confirm with the customer.",
            break_loop=False,
        )
