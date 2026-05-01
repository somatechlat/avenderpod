"""
Centralized message strings and codes for the admin application.
This follows the Vibe Coding Rules (Rule 11: NO Hardcoded Strings).
"""

MESSAGES = {
    # General / Auth
    "ERR_UNAUTHORIZED": "No tienes permisos para realizar esta acción.",
    "ERR_NOT_FOUND": "El recurso solicitado no fue encontrado.",
    "ERR_INVALID_PAYLOAD": "Los datos proporcionados son inválidos.",
    # Tenants
    "SUCCESS_TENANT_CREATED": "El inquilino (Tenant) '{name}' ha sido creado exitosamente.",
    "ERR_TENANT_CREATION_FAILED": "Ocurrió un error al crear el inquilino: {detail}",
    # Infrastructure (Vultr)
    "SUCCESS_POD_SUSPENDED": "El pod del inquilino '{name}' ha sido suspendido.",
    "SUCCESS_POD_REACTIVATED": "El pod del inquilino '{name}' ha sido reactivado.",
    "ERR_VULTR_API_FAILED": "Error en la infraestructura (Vultr): {detail}",
    # Config / Catalog
    "SUCCESS_CONFIG_SAVED": "Configuración guardada exitosamente.",
    "SUCCESS_CATALOG_ITEM_CREATED": "Item del catálogo '{name}' creado exitosamente.",
    # Tenant Deployment & Validation
    "ERR_PLAN_REQUIRED": "Active plan is required before tenant deployment.",
    "ERR_PLAN_INACTIVE": "Selected plan is inactive.",
    "ERR_MISSING_TENANT_INFO": "Business name and owner name are required.",
    "ERR_INVALID_PHONE": "Owner phone must be in E.164 format (+1234567890).",
    # Auth & God Mode
    "SUCCESS_CHALLENGE_INITIATED": "Challenge initiated.",
    "ERR_MASTER_PASSWORD_INVALID": "Invalid Master Password.",
    "ERR_PIN_INVALID": "Invalid or expired Session PIN.",
    "ERR_PIN_EXPIRED": "Session PIN has expired.",
    "SUCCESS_CREATOR_ACCESS": "Creator access granted.",
}


def get_message(code: str, **kwargs) -> str:
    """
    Retrieve a localized/formatted message string by code.
    If the code does not exist, returns a fallback error string.
    """
    message_template = MESSAGES.get(
        code, f"Mensaje no encontrado para el código: {code}"
    )
    try:
        return message_template.format(**kwargs)
    except KeyError as e:
        return f"{message_template} (Missing format variable: {e})"
