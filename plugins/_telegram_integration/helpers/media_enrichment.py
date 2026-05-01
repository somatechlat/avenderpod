"""Telegram media and location enrichment helpers."""

from __future__ import annotations

import os
import uuid
import base64

from aiogram.types import Message as TgMessage

from helpers import files, whisper
from helpers.print_style import PrintStyle
from plugins._telegram_integration.helpers import telegram_client as tc
from plugins._telegram_integration.helpers.constants import DOWNLOAD_FOLDER


AUDIO_EXTENSIONS = {".ogg", ".opus", ".mp3", ".wav", ".m4a", ".aac", ".flac"}


def extract_message_content(message: TgMessage) -> str:
    parts = []

    if message.text:
        parts.append(message.text)
    elif message.caption:
        parts.append(message.caption)

    if message.location:
        loc = message.location
        parts.append(f"[Location: {loc.latitude}, {loc.longitude}]")

    if message.contact:
        c = message.contact
        parts.append(
            f"[Contact: {c.first_name} {c.last_name or ''} phone={c.phone_number}]"
        )

    if message.sticker:
        parts.append(f"[Sticker: {message.sticker.emoji or ''}]")

    for attr, label in [("voice", "Voice message"), ("video_note", "Video note")]:
        if getattr(message, attr, None):
            parts.append(f"[{label} - see attachment]")

    return "\n".join(parts) if parts else "[No text content]"


async def download_attachments(
    bot, message: TgMessage, bot_name: str = ""
) -> list[str]:
    paths: list[str] = []
    tg_prefix = f"tg_{bot_name}_" if bot_name else "tg_"
    download_dir = files.get_abs_path(DOWNLOAD_FOLDER)
    os.makedirs(download_dir, exist_ok=True)
    download_dir_ref = files.get_abs_path_dockerized(DOWNLOAD_FOLDER)

    async def _dl(file_id: str, filename: str) -> str | None:
        safe_name = f"{tg_prefix}{uuid.uuid4().hex[:8]}_{filename}"
        dest = os.path.join(download_dir, safe_name)
        result = await tc.download_file(bot, file_id, dest)
        if result:
            return os.path.join(download_dir_ref, safe_name)
        return None

    if message.photo:
        photo = message.photo[-1]
        path = await _dl(photo.file_id, f"photo_{photo.file_unique_id}.jpg")
        if path:
            paths.append(path)

    attachment_types = [
        ("document", "file", None),
        ("audio", "audio", ".mp3"),
        ("voice", "voice", ".ogg"),
        ("video", "video", ".mp4"),
        ("video_note", "videonote", ".mp4"),
    ]
    for attr, prefix, ext in attachment_types:
        obj = getattr(message, attr, None)
        if not obj:
            continue
        fname = (
            getattr(obj, "file_name", None)
            or f"{prefix}_{obj.file_unique_id}{ext or ''}"
        )
        path = await _dl(obj.file_id, fname)
        if path:
            paths.append(path)

    return paths


async def enrich_message_text(
    message: TgMessage,
    text: str,
    attachments: list[str],
) -> str:
    parts = [text] if text else []

    transcript = await transcribe_first_audio(attachments)
    if transcript:
        parts.append(f"[Nota de voz transcrita]: {transcript}")

    location_block = build_location_block(message)
    if location_block:
        parts.append(location_block)

    return "\n".join(part for part in parts if part).strip() or "[No text content]"


async def transcribe_first_audio(attachments: list[str]) -> str:
    audio_path = next((_local_audio_path(path) for path in attachments), "")
    if not audio_path:
        return ""

    try:
        with open(audio_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        data = await whisper.transcribe("base", encoded, language="es")
        return str(data.get("text", "")).strip()
    except Exception as e:
        PrintStyle.warning(f"Telegram: whisper error: {e}")
        return ""


def build_location_block(message: TgMessage) -> str:
    loc = message.location
    if not loc:
        return ""

    details = [
        "[UBICACIÓN RECIBIDA POR TELEGRAM]",
        f"Coordenadas: {loc.latitude}, {loc.longitude}",
    ]
    horizontal_accuracy = getattr(loc, "horizontal_accuracy", None)
    if horizontal_accuracy is not None:
        details.append(f"Precisión aproximada: {horizontal_accuracy} m")
    live_period = getattr(loc, "live_period", None)
    if live_period is not None:
        details.append(f"Ubicación en vivo: {live_period} segundos")

    details.append(
        "\n(SISTEMA: El usuario ha enviado su ubicación por Telegram. "
        "Debes usar la herramienta 'process_location' con estas coordenadas "
        "para confirmar la zona de entrega y responder de forma corta "
        "confirmando el sector/calle como se indica en tus reglas.)"
    )
    return "\n".join(details)


def _local_audio_path(path: str) -> str:
    local_path = files.fix_dev_path(path)
    if not os.path.isfile(local_path):
        return ""
    ext = os.path.splitext(local_path.lower())[1]
    if ext not in AUDIO_EXTENSIONS:
        return ""
    return local_path
