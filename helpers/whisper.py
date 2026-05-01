import os
import base64
import asyncio
import tempfile
from typing import Any

from helpers.print_style import PrintStyle

_models: dict[str, Any] = {}
_model_locks: dict[str, asyncio.Lock] = {}
_downloaded_models: set[str] = set()


def _normalize_model_name(model_name: str | None) -> str:
    return (model_name or os.environ.get("STT_MODEL_SIZE") or "base").strip() or "base"


async def preload(model_name: str):
    return await _preload(model_name)


async def _preload(model_name: str):
    model_name = _normalize_model_name(model_name)
    if model_name in _models:
        return True

    lock = _model_locks.setdefault(model_name, asyncio.Lock())
    async with lock:
        if model_name in _models:
            return True
        try:
            import whisper

            PrintStyle.standard(f"Loading local Whisper model: {model_name}")
            _models[model_name] = await asyncio.to_thread(whisper.load_model, model_name)
            _downloaded_models.add(model_name)
            return True
        except Exception as e:
            PrintStyle.error(f"Failed to load local Whisper model {model_name}: {e}")
            raise


async def is_downloading():
    return False


async def is_downloaded():
    return bool(_downloaded_models)


async def transcribe(
    model_name: str,
    audio_bytes_b64: str,
    language: str | None = None,
):
    return await _transcribe(model_name, audio_bytes_b64, language=language)


async def _transcribe(
    model_name: str,
    audio_bytes_b64: str,
    language: str | None = None,
):
    model_name = _normalize_model_name(model_name)
    language = (language or os.environ.get("STT_LANGUAGE") or "es").strip() or "es"
    audio_bytes = base64.b64decode(audio_bytes_b64)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
        audio_file.write(audio_bytes)
        temp_path = audio_file.name

    try:
        await _preload(model_name)
        model = _models[model_name]

        def _run_transcription():
            return model.transcribe(
                temp_path,
                language=language,
                fp16=False,
            )

        result = await asyncio.to_thread(_run_transcription)
        text = str(result.get("text", "")).strip()
        return {"text": text}

    except Exception as e:
        PrintStyle.error(f"Local Whisper transcription failed: {e}")
        return {"text": f"[Error de transcripción local: {str(e)}]"}
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass
