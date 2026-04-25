import json

from helpers.tool import Tool, Response
from helpers.print_style import PrintStyle
from usr.plugins.avender.helpers.db import get_connection


class UpdateCatalogItem(Tool):
    """
    Updates or creates a catalog item. Used exclusively during OWNER MODE
    (admin backdoor) for conversational catalog management via WhatsApp.
    (SRS REQ-3.4.4)
    """

    name = "update_catalog_item"
    description = (
        "Updates an existing catalog item or creates a new one. "
        "Use this ONLY in ADMIN/OWNER MODE to modify prices, names, "
        "descriptions, or metadata of catalog items."
    )
    parameters = {
        "type": "object",
        "properties": {
            "item_name": {
                "type": "string",
                "description": "Name of the item to update or create.",
            },
            "new_price": {
                "type": "number",
                "description": "New price for the item (optional if only updating other fields).",
            },
            "new_description": {
                "type": "string",
                "description": "New description for the item (optional).",
            },
            "new_name": {
                "type": "string",
                "description": "Rename the item (optional).",
            },
            "metadata_updates": {
                "type": "string",
                "description": "JSON string of metadata fields to update (optional).",
            },
        },
        "required": ["item_name"],
    }

    async def execute(
        self,
        item_name: str,
        new_price: float | None = None,
        new_description: str | None = None,
        new_name: str | None = None,
        metadata_updates: str | None = None,
        **kwargs,
    ):
        conn = get_connection()
        cursor = conn.cursor()

        # Find existing item by fuzzy name match
        cursor.execute(
            "SELECT id, name, price, description, metadata FROM catalog_item WHERE name LIKE ? LIMIT 1",
            (f"%{item_name}%",),
        )
        row = cursor.fetchone()

        if row:
            # Update existing item
            item_id = row["id"]
            updates: list[str] = []
            params: list = []

            if new_price is not None:
                updates.append("price = ?")
                params.append(float(new_price))

            if new_description is not None:
                updates.append("description = ?")
                params.append(new_description)

            if new_name is not None:
                updates.append("name = ?")
                params.append(new_name)

            if metadata_updates:
                try:
                    meta_dict = (
                        json.loads(metadata_updates)
                        if isinstance(metadata_updates, str)
                        else metadata_updates
                    )
                    # Merge with existing metadata
                    existing_meta = json.loads(row["metadata"] or "{}")
                    existing_meta.update(meta_dict)
                    updates.append("metadata = ?")
                    params.append(json.dumps(existing_meta))
                except (json.JSONDecodeError, TypeError):
                    pass  # Ignore invalid metadata, process other updates

            if not updates:
                conn.close()
                return Response(
                    message=f"No changes specified for '{row['name']}'. Provide new_price, new_description, new_name, or metadata_updates.",
                    break_loop=False,
                )

            params.append(item_id)
            sql = f"UPDATE catalog_item SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, params)
            conn.commit()
            conn.close()

            display_name = new_name or row["name"]
            display_price = (
                f"${new_price:.2f}" if new_price is not None else f"${row['price']:.2f}"
            )
            PrintStyle.success(
                f"Avender: Updated catalog item '{display_name}' → {display_price}"
            )
            return Response(
                message=f"✅ Ítem '{display_name}' actualizado exitosamente. Precio: {display_price}",
                break_loop=False,
            )

        else:
            # Create new item
            if new_price is None:
                conn.close()
                return Response(
                    message=f"El ítem '{item_name}' no existe en el catálogo. Para crearlo, especifica también el precio (new_price).",
                    break_loop=False,
                )

            meta_str = "{}"
            if metadata_updates:
                try:
                    meta_str = (
                        json.dumps(json.loads(metadata_updates))
                        if isinstance(metadata_updates, str)
                        else json.dumps(metadata_updates)
                    )
                except (json.JSONDecodeError, TypeError):
                    meta_str = "{}"

            cursor.execute(
                "INSERT INTO catalog_item (name, price, description, metadata) VALUES (?, ?, ?, ?)",
                (item_name, float(new_price), new_description or "", meta_str),
            )
            conn.commit()
            conn.close()

            PrintStyle.success(
                f"Avender: Created new catalog item '{item_name}' at ${new_price:.2f}"
            )
            return Response(
                message=f"✅ Nuevo ítem '{item_name}' creado exitosamente. Precio: ${new_price:.2f}",
                break_loop=False,
            )
