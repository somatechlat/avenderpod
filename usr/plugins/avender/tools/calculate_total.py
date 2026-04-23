import json

from helpers.tool import Tool, Response
from helpers.print_style import PrintStyle
from usr.plugins.avender.helpers.db import get_connection


class CalculateTotal(Tool):
    """
    Calculates the total cost of items in a customer's order.
    Queries the catalog for current prices and applies delivery charges
    when specified. (SRS REQ-3.2.3, declared in agent.yaml)
    """

    name = "calculate_total"
    description = (
        "Calculates the total cost of one or more items from the catalog, "
        "including optional delivery charge. Use this before confirming an order."
    )
    parameters = {
        "type": "object",
        "properties": {
            "items": {
                "type": "string",
                "description": (
                    "JSON array of objects with 'name' (str) and 'quantity' (int). "
                    'Example: [{"name": "hamburguesa doble", "quantity": 2}]'
                ),
            },
            "delivery_charge": {
                "type": "number",
                "description": "Optional delivery charge to add (default 0).",
            },
        },
        "required": ["items"],
    }

    async def execute(self, items: str, delivery_charge: float = 0.0, **kwargs):
        try:
            item_list = json.loads(items) if isinstance(items, str) else items
        except (json.JSONDecodeError, TypeError) as e:
            return Response(
                message=f"Error parsing items: {e}. Send a valid JSON array.",
                break_loop=False,
            )

        if not isinstance(item_list, list) or not item_list:
            return Response(
                message="Items must be a non-empty list of {name, quantity} objects.",
                break_loop=False,
            )

        conn = get_connection()
        cursor = conn.cursor()

        total = 0.0
        breakdown_lines: list[str] = []
        missing_items: list[str] = []

        for entry in item_list:
            name = entry.get("name", "").strip()
            qty = int(entry.get("quantity", 1))
            if qty < 1:
                qty = 1

            # Fuzzy search by name
            cursor.execute(
                "SELECT name, price FROM catalog_item WHERE name LIKE ? LIMIT 1",
                (f"%{name}%",),
            )
            row = cursor.fetchone()
            if row:
                item_total = row["price"] * qty
                total += item_total
                breakdown_lines.append(
                    f"  {row['name']} x{qty} = ${item_total:.2f}"
                )
            else:
                missing_items.append(name)

        conn.close()

        if missing_items:
            missing_str = ", ".join(missing_items)
            return Response(
                message=(
                    f"No se encontraron estos ítems en el catálogo: {missing_str}. "
                    "Verifica la ortografía o pregunta al cliente qué desea."
                ),
                break_loop=False,
            )

        delivery_charge = float(delivery_charge or 0)
        if delivery_charge > 0:
            breakdown_lines.append(f"  Delivery: ${delivery_charge:.2f}")
            total += delivery_charge

        breakdown = "\n".join(breakdown_lines)
        result = (
            f"Desglose del pedido:\n{breakdown}\n"
            f"TOTAL: ${total:.2f}"
        )
        PrintStyle.success(f"Avender calculate_total: ${total:.2f}")
        return Response(message=result, break_loop=False)
