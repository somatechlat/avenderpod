import hashlib
import hmac
import json
import time
import uuid

import requests as http_requests

from agent import AgentContext, UserMessage
from helpers.api import ApiHandler, Request, Response
from helpers.persist_chat import save_tmp_chat
from helpers.plugins import get_plugin_config
from helpers.print_style import PrintStyle
from initialize import initialize_agent

AVENDER_AGENT_PROFILE = "avender_sales"

from usr.plugins.avender.helpers.db import get_tenant_config


def _get_avender_config() -> dict:
    """Retrieve avender plugin config from the A0 plugin config system."""
    return get_plugin_config("avender") or {}

# ---------------------------------------------------------------
# Stateful Admin Session Tracker
# Key = WA sender identifier, Value = expiry timestamp (epoch)
# Admin sessions auto-expire after ADMIN_TIMEOUT_SECONDS.
# ---------------------------------------------------------------
ADMIN_TIMEOUT_SECONDS = 600  # 10 minutes (SRS Rec 4)
_admin_sessions: dict[str, float] = {}

# ---------------------------------------------------------------
# Rate Limiter (SRS Rec 6)
# Token-bucket per sender — prevents LLM billing spikes from spam.
# ---------------------------------------------------------------
RATE_LIMIT_WINDOW_SECONDS = 60
MAX_MESSAGES_PER_WINDOW = 15
_rate_buckets: dict[str, list[float]] = {}  # sender_id → list of timestamps


def _is_rate_limited(sender_id: str) -> bool:
    """Check if sender exceeds the message rate limit (SRS Rec 6).
    Returns True if the sender should be blocked."""
    now = time.time()
    bucket = _rate_buckets.get(sender_id, [])
    # Prune timestamps outside the window
    bucket = [ts for ts in bucket if now - ts < RATE_LIMIT_WINDOW_SECONDS]
    if len(bucket) >= MAX_MESSAGES_PER_WINDOW:
        _rate_buckets[sender_id] = bucket
        return True
    bucket.append(now)
    _rate_buckets[sender_id] = bucket
    return False

# Map sender_id → AgentContext.id for routing continuations
_sender_contexts: dict[str, str] = {}

PLUGIN_NAME = "avender"


def _verify_webhook_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
    """Validate HMAC-SHA256 signature from Chatwoot webhook (SRS Rec 5)."""
    if not secret:
        PrintStyle.warning("Avender: webhook_secret not configured. Skipping signature validation.")
        return True
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _is_admin_active(sender_id: str) -> bool:
    """Check if sender has an active, non-expired admin session."""
    expiry = _admin_sessions.get(sender_id)
    if expiry is None:
        return False
    if time.time() > expiry:
        # Expired — clean up
        _admin_sessions.pop(sender_id, None)
        return False
    return True


def _activate_admin(sender_id: str) -> None:
    """Activate admin session with timeout (SRS REQ-3.4.3)."""
    _admin_sessions[sender_id] = time.time() + ADMIN_TIMEOUT_SECONDS


def _deactivate_admin(sender_id: str) -> None:
    """End admin session."""
    _admin_sessions.pop(sender_id, None)


def _transcribe_audio(audio_url: str) -> str:
    """Download OGG from Chatwoot and route to Tier 1.5 Whisper (SRS REQ-3.3.3)."""
    PrintStyle.info(f"Avender: Downloading WhatsApp audio from {audio_url}...")
    audio_res = http_requests.get(audio_url, timeout=15)
    audio_res.raise_for_status()

    PrintStyle.info("Avender: Routing OGG to Centralized Whisper Server...")
    whisper_res = http_requests.post(
        "http://whisper_server:8000/v1/audio/transcriptions",
        files={"file": ("audio.ogg", audio_res.content, "audio/ogg")},
        data={"model": "whisper-1", "language": "es"},
        timeout=45,
    )
    whisper_res.raise_for_status()
    transcribed = whisper_res.json().get("text", "").strip()
    PrintStyle.success(f"Avender: Transcribed audio: {transcribed[:80]}...")
    return transcribed


def _reply_via_chatwoot(conversation_id: str, message: str) -> None:
    """Send a reply back through Chatwoot API (SRS REQ-3.3.1)."""
    config = _get_avender_config()
    cw_url = config.get("chatwoot_url", "")
    cw_token = config.get("chatwoot_api_token", "")
    if not cw_url or not cw_token:
        PrintStyle.error("Avender: chatwoot_url or chatwoot_api_token not configured.")
        return

    # Chatwoot API: POST /api/v1/accounts/{account_id}/conversations/{id}/messages
    account_id = config.get("chatwoot_account_id", "1")
    endpoint = f"{cw_url.rstrip('/')}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
    try:
        resp = http_requests.post(
            endpoint,
            json={"content": message, "message_type": "outgoing"},
            headers={"api_access_token": cw_token},
            timeout=15,
        )
        resp.raise_for_status()
        PrintStyle.success(f"Avender: Reply sent to conversation {conversation_id}")
    except Exception as e:
        PrintStyle.error(f"Avender: Failed to send reply via Chatwoot: {e}")


class ChatwootWebhookHandler(ApiHandler):
    """
    Receives incoming Webhooks from the centralized Chatwoot Avender Systems Control Panel.
    Route: /api/plugins/avender/chatwoot

    Implements:
      - HMAC signature validation (SRS Rec 5)
      - Audio transcription via Whisper (SRS REQ-3.3.3)
      - Stateful admin backdoor with 10-min timeout (SRS REQ-3.4.1–3.4.4, Rec 4)
      - Real routing to Agent Zero cognitive loop (SRS REQ-3.3.1)
    """

    @classmethod
    def requires_auth(cls) -> bool:
        return False  # Chatwoot sends webhooks without A0 auth

    @classmethod
    def requires_csrf(cls) -> bool:
        return False  # External webhook, no browser CSRF

    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            # -------------------------------------------------------
            # 1. Webhook Signature Validation (SRS Rec 5)
            # -------------------------------------------------------
            config = _get_avender_config()
            webhook_secret = config.get("webhook_secret", "")
            raw_body = json.dumps(input).encode()
            signature = ""
            if hasattr(request, "headers"):
                signature = request.headers.get("X-Chatwoot-Signature", "") or ""
            if webhook_secret and signature:
                if not _verify_webhook_signature(raw_body, signature, webhook_secret):
                    PrintStyle.error("Avender: Invalid webhook signature. Rejecting request.")
                    return {"ok": False, "error": "Invalid webhook signature"}

            # -------------------------------------------------------
            # 2. Extract core message data
            # -------------------------------------------------------
            event_type = input.get("event", "message_created")
            if event_type != "message_created":
                return {"ok": True, "status": "ignored_event"}

            # Skip outgoing messages (our own replies)
            message_type = input.get("message_type")
            if message_type == "outgoing":
                return {"ok": True, "status": "ignored_outgoing"}

            message_content = (input.get("content") or "").strip()
            sender = input.get("sender") or {}
            sender_id = sender.get("identifier") or sender.get("id") or "unknown"
            sender_name = sender.get("name") or "Cliente"
            conversation = input.get("conversation") or {}
            conversation_id = str(conversation.get("id", input.get("conversation_id", "")))

            # -------------------------------------------------------
            # 3. Audio Transcription (SRS REQ-3.3.3)
            # -------------------------------------------------------
            attachments = input.get("attachments") or []
            for att in attachments:
                if att.get("file_type") == "audio":
                    audio_url = att.get("data_url")
                    if audio_url:
                        try:
                            transcribed = _transcribe_audio(audio_url)
                            message_content = f"[Transcripción de Audio]: {transcribed}"
                        except Exception as e:
                            PrintStyle.error(f"Avender: Whisper transcription failed: {e}")
                            message_content = "[El audio no pudo ser transcrito. Por favor, envíe un mensaje de texto.]"
                    break  # Process only the first audio attachment

            if not message_content:
                return {"ok": True, "status": "empty_message"}

            # -------------------------------------------------------
            # 3b. Rate Limiting (SRS Rec 6)
            # -------------------------------------------------------
            if _is_rate_limited(str(sender_id)):
                PrintStyle.warning(f"Avender: Rate limited sender {sender_id}")
                return {"ok": True, "status": "rate_limited"}

            # -------------------------------------------------------
            # 4. Admin Backdoor — Stateful Session Management
            #    (SRS REQ-3.4.1, 3.4.2, 3.4.3, 3.4.4, Rec 4)
            # -------------------------------------------------------
            upper_msg = message_content.upper().strip()

            # Trigger phrases (SRS REQ-3.4.2)
            if upper_msg in ("OWNER MODE", "ACTIVATE ADMIN ROLE"):
                reply = "🔐 MODO DUEÑO ACTIVADO. Por favor, ingrese su PIN de seguridad."
                _reply_via_chatwoot(conversation_id, reply)
                return {"ok": True, "status": "admin_pin_challenge"}

            # PIN verification
            config = _get_avender_config()
            admin_pin = config.get("admin_pin", "")
            if admin_pin and message_content.strip() == admin_pin and not _is_admin_active(sender_id):
                _activate_admin(sender_id)
                reply = (
                    "✅ PIN Correcto. Sesión de administrador activada por 10 minutos.\n"
                    "Escriba cambios en lenguaje natural (Ej: 'Cambia la hamburguesa a $10').\n"
                    "Escriba 'SALIR' o 'EXIT OWNER MODE' para terminar."
                )
                _reply_via_chatwoot(conversation_id, reply)
                return {"ok": True, "status": "admin_activated"}

            # Exit admin mode
            if upper_msg in ("SALIR", "EXIT OWNER MODE") and _is_admin_active(sender_id):
                _deactivate_admin(sender_id)
                reply = "🔒 Modo Dueño Desactivado. El asistente de ventas retoma el control."
                _reply_via_chatwoot(conversation_id, reply)
                return {"ok": True, "status": "admin_deactivated"}

            # If admin session active, route to admin agent context (REQ-3.4.4)
            # The admin context uses the same agent but with catalog update tools enabled
            if _is_admin_active(sender_id):
                # Refresh timeout on activity
                _activate_admin(sender_id)
                # Route admin commands through the cognitive engine with admin flag
                context = self._get_or_create_context(sender_id, sender_name, is_admin=True)
                msg_id = str(uuid.uuid4())
                admin_prompt = (
                    f"[MODO ADMINISTRADOR] El dueño del negocio dice: {message_content}\n"
                    "Tienes acceso temporal a update_catalog_item. Ejecuta el cambio solicitado."
                )
                context.communicate(UserMessage(message=admin_prompt, id=msg_id))
                save_tmp_chat(context)
                return {"ok": True, "status": "admin_command_routed", "context_id": context.id}

            # -------------------------------------------------------
            # 5. Normal Sales Mode — Route to Agent Zero Cognitive Loop
            #    (SRS REQ-3.3.1, REQ-3.2.1)
            # -------------------------------------------------------
            context = self._get_or_create_context(sender_id, sender_name, is_admin=False)

            # Store conversation_id for reply routing
            context.data["cw_conversation_id"] = conversation_id
            context.data["cw_sender_id"] = sender_id
            context.data["cw_sender_name"] = sender_name

            msg_id = str(uuid.uuid4())
            context.communicate(UserMessage(message=message_content, id=msg_id))
            save_tmp_chat(context)

            PrintStyle.success(
                f"Avender: Message from {sender_name} ({sender_id}) routed to context {context.id}"
            )
            return {"ok": True, "status": "routed", "context_id": context.id}

        except Exception as e:
            PrintStyle.error(f"Avender Webhook Error: {e}")
            return {"ok": False, "error": str(e)}

    def _get_or_create_context(
        self, sender_id: str, sender_name: str, *, is_admin: bool
    ) -> AgentContext:
        """Retrieve existing AgentContext for this sender or create a new one."""
        existing_id = _sender_contexts.get(sender_id)
        if existing_id:
            context = AgentContext.get(existing_id)
            if context is not None:
                return context
            # Context was garbage-collected — remove stale reference
            _sender_contexts.pop(sender_id, None)

        # Create new context with the avender_sales agent profile
        agent_config = initialize_agent(
            override_settings={"agent_profile": AVENDER_AGENT_PROFILE}
        )
        label = f"AVENDER {'Admin' if is_admin else 'Sales'}: {sender_name[:50]}"
        context = AgentContext(agent_config, name=label)

        # Store mapping for future message routing
        _sender_contexts[sender_id] = context.id

        PrintStyle.success(f"Avender: Created new context {context.id} for {sender_name}")
        return context
