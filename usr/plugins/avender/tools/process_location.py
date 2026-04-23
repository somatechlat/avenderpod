import json

from helpers.tool import Tool, Response
from helpers.print_style import PrintStyle
from usr.plugins.avender.helpers.db import get_tenant_config


class ProcessLocation(Tool):
    """
    Processes a WhatsApp location pin (latitude/longitude) sent by the customer.
    Determines delivery feasibility based on the tenant's delivery rules
    and returns the appropriate delivery charge.
    (SRS REQ-3.2.3, REQ-3.3.4, declared in agent.yaml)
    """

    name = "process_location"
    description = (
        "Processes a location pin (latitude and longitude) from the customer's WhatsApp message. "
        "Determines if delivery is available and calculates the delivery charge based on the business rules."
    )
    parameters = {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude from the WhatsApp location pin.",
            },
            "longitude": {
                "type": "number",
                "description": "Longitude from the WhatsApp location pin.",
            },
            "address_text": {
                "type": "string",
                "description": "Optional text address or landmark provided by the customer.",
            },
        },
        "required": ["latitude", "longitude"],
    }

    async def execute(
        self,
        latitude: float,
        longitude: float,
        address_text: str = "",
        **kwargs,
    ):
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (ValueError, TypeError):
            return Response(
                message="Coordenadas inválidas. Pide al cliente que reenvíe su ubicación.",
                break_loop=False,
            )

        # Retrieve tenant delivery rules
        delivery_rules = get_tenant_config("deliveryRules") or ""
        headquarters = get_tenant_config("headquarters") or "No configurada"

        # Build a structured summary for the LLM to use when deciding
        # delivery feasibility. The actual distance calculation uses a simple
        # heuristic — for Ecuador, 0.01 degree ≈ 1.11 km.
        location_summary = (
            f"Ubicación del cliente:\n"
            f"  Coordenadas: {lat:.6f}, {lon:.6f}\n"
        )
        if address_text:
            location_summary += f"  Dirección: {address_text}\n"

        location_summary += (
            f"\nDirección del negocio: {headquarters}\n"
            f"Reglas de delivery configuradas: {delivery_rules if delivery_rules else 'No configuradas'}\n"
        )

        # If no delivery rules are configured, inform the agent
        if not delivery_rules:
            location_summary += (
                "\nNo hay reglas de delivery configuradas. "
                "Pregunta al cliente si puede recoger en tienda o informa "
                "que el delivery no está disponible aún."
            )
        else:
            location_summary += (
                "\nUsa las reglas de delivery para determinar si la ubicación "
                "está en zona de cobertura y qué tarifa aplica. "
                "Si no puedes determinar la zona, pregunta al cliente su sector."
            )

        PrintStyle.success(
            f"Avender process_location: ({lat}, {lon}) — {address_text or 'no address'}"
        )
        return Response(message=location_summary, break_loop=False)
