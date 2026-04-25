from helpers.tool import Tool, Response
from usr.plugins.avender.helpers.db import get_connection


class SearchCatalog(Tool):
    name = "search_catalog"
    description = (
        "Searches the business catalog for products or services based on a query."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The item to search for."}
        },
        "required": ["query"],
    }

    async def execute(self, query: str, **kwargs):
        conn = get_connection()
        cursor = conn.cursor()
        # Search in name or description using simple wildcard
        cursor.execute(
            "SELECT name, price, description, metadata FROM catalog_item WHERE name LIKE ? OR description LIKE ?",
            (f"%{query}%", f"%{query}%"),
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not results:
            return Response(
                message="No items found matching the query in the database.",
                break_loop=False,
            )
        return Response(message=f"Found items: {results}", break_loop=False)
