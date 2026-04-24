import base64
import warnings
import tempfile
import asyncio
import os
import requests
from helpers import runtime, rfc, settings, files as file_helpers
from helpers.print_style import PrintStyle
from helpers.notification import NotificationManager, NotificationType, NotificationPriority

# Whisper API Configuration — OpenAI-compatible endpoint on faster-whisper-server
WHISPER_API_URL = os.environ.get("WHISPER_API_URL", "http://avender_whisper:8000/v1/audio/transcriptions")

async def preload(model_name:str):
    # Remote API doesn't need preloading in the same way, but we'll keep the signature
    PrintStyle.standard(f"Whisper remote API active: {model_name}")
    return True
        
async def _preload(model_name:str):
    return True

async def is_downloading():
    return False

async def is_downloaded():
    return True

async def transcribe(model_name:str, audio_bytes_b64: str):
    return await _transcribe(model_name, audio_bytes_b64)

async def _transcribe(model_name:str, audio_bytes_b64: str):
    # Decode audio bytes if encoded as a base64 string
    audio_bytes = base64.b64decode(audio_bytes_b64)

    # Create temp audio file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
        audio_file.write(audio_bytes)
        temp_path = audio_file.name
    
    try:
        # Transcribe using remote API (OpenAI-compatible multipart format)
        with open(temp_path, 'rb') as f:
            form_files = {'file': (os.path.basename(temp_path), f, 'audio/wav')}
            form_data = {'model': 'whisper-1'}
            response = requests.post(
                WHISPER_API_URL, files=form_files, data=form_data, timeout=60
            )
            
        if response.status_code == 200:
            return response.json()
        else:
            PrintStyle.error(f"Whisper API error: {response.status_code} - {response.text}")
            return {"text": "[Error en transcripción externa]"}
            
    except Exception as e:
        PrintStyle.error(f"Failed to connect to Whisper API: {str(e)}")
        return {"text": f"[Error de conexión: {str(e)}]"}
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass # ignore errors during cleanup
