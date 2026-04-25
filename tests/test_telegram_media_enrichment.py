from types import SimpleNamespace
from typing import Any, cast

import pytest

from plugins._telegram_integration.helpers import media_enrichment


def test_location_block_instructs_avender_process_location():
    message = SimpleNamespace(
        location=SimpleNamespace(
            latitude=-2.170998,
            longitude=-79.922359,
            horizontal_accuracy=15,
            live_period=None,
        )
    )

    block = media_enrichment.build_location_block(cast(Any, message))

    assert "[UBICACIÓN RECIBIDA POR TELEGRAM]" in block
    assert "Coordenadas: -2.170998, -79.922359" in block
    assert "process_location" in block


@pytest.mark.asyncio
async def test_enrich_message_text_keeps_text_and_location_without_audio():
    message = SimpleNamespace(
        location=SimpleNamespace(
            latitude=-2.170998,
            longitude=-79.922359,
            horizontal_accuracy=None,
            live_period=None,
        )
    )

    text = await media_enrichment.enrich_message_text(cast(Any, message), "Hola", [])

    assert text.startswith("Hola")
    assert "Coordenadas: -2.170998, -79.922359" in text
    assert "process_location" in text
