"""
Avender Onboarding Handler — submits wizard data into tenant SQLite DB.
Refactored to stay under 650 lines. Business logic extracted to helpers.
"""

from helpers.api import ApiHandler, Request, Response
from helpers.print_style import PrintStyle
from usr.plugins.avender.helpers.auth import PASSWORD_KEY, hash_admin_password
from usr.plugins.avender.helpers.config import normalize_settings
from usr.plugins.avender.helpers.db import get_connection
from usr.plugins.avender.helpers.onboarding_presets import ALLOWED_ARCHETYPES
from usr.plugins.avender.helpers.onboarding_validators import (
    ID_PATTERNS,
    _sanitize_text,
    _validate_whatsapp_number,
    _validate_url,
    validate_catalog_items,
)
from usr.plugins.avender.helpers.onboarding_business import configure_whatsapp, save_catalog
from usr.plugins.avender.helpers.setup_auth import require_setup_token
import json


class AvenderOnboardingHandler(ApiHandler):
    """
    Handles submission from the Onboarding Wizard.
    Route: /api/plugins/avender/onboarding_api
    """

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        conn = None
        try:
            # 1. Atomic gate: reject if onboarding already completed (must come first
            # so that the frontend probe with an empty body gets the correct redirect signal)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                "SELECT 1 FROM tenant_config WHERE key = 'onboarding_complete' AND value = 'true'"
            )
            if cursor.fetchone():
                conn.rollback()
                conn.close()
                conn = None
                return {"ok": False, "error": "Onboarding already completed."}
            # We keep the transaction open; conn is not None here.

            setup_error = require_setup_token(input, request)
            if setup_error:
                conn.rollback()
                conn.close()
                conn = None
                return setup_error

            # 2. Validate required fields
            required_fields = [
                "idType", "idNumber", "tradeName", "headquarters",
                "archetype", "whatsappNumber", "adminPassword",
            ]
            missing = []
            for field in required_fields:
                value = input.get(field)
                if value is None or (isinstance(value, str) and not value.strip()) or (not isinstance(value, str) and not value):
                    missing.append(field)
            if missing:
                conn.rollback()
                conn.close()
                conn = None
                return {"ok": False, "error": f"Faltan campos obligatorios: {', '.join(missing)}"}

            # 3. Extract and validate inputs
            id_type = str(input.get("idType", "")).lower()
            id_number = str(input.get("idNumber", "")).strip()
            trade_name = str(input.get("tradeName", "")).strip()
            legal_name = str(input.get("legalName", "")).strip()
            headquarters = str(input.get("headquarters", "")).strip()
            whatsapp_number = str(input.get("whatsappNumber", "")).strip()
            admin_password = str(input.get("adminPassword", ""))
            archetype = str(input.get("archetype", "")).lower()
            payment_url = str(input.get("paymentUrl", "")).strip()
            restrict_access = bool(input.get("restrictAccess") or input.get("enableWhitelist"))
            input["restrictAccess"] = restrict_access

            if id_type not in ID_PATTERNS:
                conn.rollback(); conn.close(); conn = None
                return {"ok": False, "error": f"Tipo de ID no válido: {id_type}. Use: ruc, cedula, passport."}
            if not ID_PATTERNS[id_type].match(id_number):
                conn.rollback(); conn.close(); conn = None
                return {"ok": False, "error": f"Número de {id_type} no válido."}

            if len(trade_name) < 2 or len(trade_name) > 200:
                conn.rollback(); conn.close(); conn = None
                return {"ok": False, "error": "El nombre comercial debe tener entre 2 y 200 caracteres."}
            if len(headquarters) < 4 or len(headquarters) > 250:
                conn.rollback(); conn.close(); conn = None
                return {"ok": False, "error": "La dirección matriz debe tener entre 4 y 250 caracteres."}

            if not _validate_whatsapp_number(whatsapp_number):
                conn.rollback(); conn.close(); conn = None
                return {"ok": False, "error": "Número de WhatsApp no válido."}

            if len(admin_password) < 8:
                conn.rollback(); conn.close(); conn = None
                return {"ok": False, "error": "La contraseña debe tener al menos 8 caracteres."}

            if archetype not in ALLOWED_ARCHETYPES:
                conn.rollback(); conn.close(); conn = None
                return {"ok": False, "error": f"Arquetipo no válido: {archetype}"}

            if payment_url and not _validate_url(payment_url):
                conn.rollback(); conn.close(); conn = None
                return {"ok": False, "error": "URL de pago no válida."}

            # 3. Validate catalog items (with safe price parsing)
            catalog_items = input.get("catalogItems", [])
            cat_ok, cat_err, validated_catalog = validate_catalog_items(catalog_items)
            if not cat_ok:
                conn.rollback(); conn.close(); conn = None
                return {"ok": False, "error": cat_err}

            # 4. Validate allowed numbers for whitelist mode
            allowed_numbers = input.get("allowedNumbers", "")
            if restrict_access:
                from plugins._whatsapp_integration.helpers.number_utils import normalize_allowed_numbers
                normalized_allowed = normalize_allowed_numbers(str(allowed_numbers))
                if not normalized_allowed:
                    conn.rollback(); conn.close(); conn = None
                    return {"ok": False, "error": "Debes agregar al menos un número permitido en Lista Blanca."}
                input["allowedNumbers"] = ",".join(sorted(normalized_allowed))
                numbers_list = [n.strip() for n in str(input["allowedNumbers"]).split(",") if n.strip()]
                if len(numbers_list) > 100:
                    conn.rollback(); conn.close(); conn = None
                    return {"ok": False, "error": "No puedes agregar más de 100 números permitidos."}

            # 5. Sanitize text inputs
            input["tradeName"] = _sanitize_text(trade_name)
            input["legalName"] = _sanitize_text(legal_name)
            input["headquarters"] = _sanitize_text(headquarters)
            input["policies"] = _sanitize_text(input.get("policies"))
            input["promotions"] = _sanitize_text(input.get("promotions"))
            input["deliveryRules"] = _sanitize_text(input.get("deliveryRules"))
            input["agentName"] = _sanitize_text(input.get("agentName"))

            # 6. Save normalized wizard data
            normalized = normalize_settings(input)
            for key, value in normalized.items():
                val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                cursor.execute(
                    "INSERT INTO tenant_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, val_str),
                )

            # 7. Store admin password hash
            cursor.execute(
                "INSERT INTO tenant_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (PASSWORD_KEY, hash_admin_password(admin_password)),
            )

            # 8. Configure WhatsApp (inside transaction — rolls back on failure)
            try:
                configure_whatsapp(cursor, normalized)
            except RuntimeError as wae:
                conn.rollback()
                conn.close()
                PrintStyle.error(f"Avender Onboarding WhatsApp Error: {wae}")
                return {"ok": False, "error": "Error configurando WhatsApp. Por favor intenta de nuevo."}

            # 9. Handle catalog items
            save_catalog(cursor, validated_catalog, archetype)

            # 10. Mark onboarding as complete
            cursor.execute(
                "INSERT INTO tenant_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("onboarding_complete", "true"),
            )

            conn.commit()
            conn.close()
            conn = None

            PrintStyle.success(
                f"Avender Onboarding: {input.get('tradeName')} ({id_type} {id_number}) — Archetype: {archetype}"
            )

            return {
                "ok": True,
                "message": "¡Configuración guardada exitosamente!",
                "tradeName": input.get("tradeName", ""),
                "archetype": archetype,
            }

        except Exception as e:
            PrintStyle.error(f"Avender Onboarding Error: {e}")
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass
            return {
                "ok": False,
                "error": "Error guardando la configuración. Por favor intenta de nuevo.",
            }
