from helpers.api import ApiHandler, Request, Response
from helpers.print_style import PrintStyle
from helpers import plugins
from plugins._whatsapp_integration.helpers.number_utils import normalize_allowed_numbers
from usr.plugins.avender.helpers.auth import PASSWORD_KEY, hash_admin_password
from usr.plugins.avender.helpers.config import normalize_settings, save_settings
from usr.plugins.avender.helpers.db import (
    save_tenant_config,
    get_tenant_config,
    get_connection,
    is_onboarding_complete,
)
import json
import os
import re
import html
import traceback

PRESETS = {
    "restaurant": [
        {
            "name": "Hamburguesa Clásica",
            "price": 0.00,
            "description": "Hamburguesa con queso, lechuga y tomate",
            "metadata": {},
        },
        {
            "name": "Papas Fritas",
            "price": 0.00,
            "description": "Porción de papas fritas crujientes",
            "metadata": {},
        },
        {
            "name": "Gaseosa",
            "price": 0.00,
            "description": "Bebida carbonatada 500ml",
            "metadata": {},
        },
        {
            "name": "Pizza Personal",
            "price": 0.00,
            "description": "Pizza de 4 porciones",
            "metadata": {},
        },
        {
            "name": "Almuerzo Ejecutivo",
            "price": 0.00,
            "description": "Sopa, plato fuerte y jugo",
            "metadata": {},
        },
        {
            "name": "Tacos",
            "price": 0.00,
            "description": "Orden de 3 tacos",
            "metadata": {},
        },
        {
            "name": "Ensalada César",
            "price": 0.00,
            "description": "Ensalada fresca con pollo",
            "metadata": {},
        },
        {
            "name": "Jugo Natural",
            "price": 0.00,
            "description": "Jugo de frutas de temporada",
            "metadata": {},
        },
        {
            "name": "Postre del Día",
            "price": 0.00,
            "description": "Postre dulce",
            "metadata": {},
        },
        {
            "name": "Café",
            "price": 0.00,
            "description": "Café pasado o americano",
            "metadata": {},
        },
    ],
    "liquor": [
        {
            "name": "Cerveza Nacional",
            "price": 0.00,
            "description": "Botella de cerveza 600ml",
            "metadata": {},
        },
        {
            "name": "Vino Tinto",
            "price": 0.00,
            "description": "Botella de vino tinto joven",
            "metadata": {},
        },
        {
            "name": "Ron",
            "price": 0.00,
            "description": "Botella de ron añejo 750ml",
            "metadata": {},
        },
        {
            "name": "Vodka",
            "price": 0.00,
            "description": "Botella de vodka 750ml",
            "metadata": {},
        },
        {
            "name": "Whisky",
            "price": 0.00,
            "description": "Botella de whisky 12 años",
            "metadata": {},
        },
        {
            "name": "Hielo",
            "price": 0.00,
            "description": "Funda de hielo en cubos",
            "metadata": {},
        },
        {
            "name": "Agua Mineral",
            "price": 0.00,
            "description": "Agua con gas 1.5L",
            "metadata": {},
        },
        {
            "name": "Gaseosa Cola",
            "price": 0.00,
            "description": "Bebida cola 3L",
            "metadata": {},
        },
        {
            "name": "Snacks",
            "price": 0.00,
            "description": "Papas fritas o nachos de funda",
            "metadata": {},
        },
        {
            "name": "Cigarrillos",
            "price": 0.00,
            "description": "Cajetilla de 20 unidades",
            "metadata": {},
        },
    ],
    "doctor": [
        {
            "name": "Consulta General",
            "price": 0.00,
            "description": "Valoración médica inicial",
            "metadata": {},
        },
        {
            "name": "Control",
            "price": 0.00,
            "description": "Cita de seguimiento",
            "metadata": {},
        },
        {
            "name": "Certificado Médico",
            "price": 0.00,
            "description": "Emisión de certificado",
            "metadata": {},
        },
        {
            "name": "Lectura de Exámenes",
            "price": 0.00,
            "description": "Revisión de resultados de laboratorio",
            "metadata": {},
        },
        {
            "name": "Telemedicina",
            "price": 0.00,
            "description": "Consulta médica virtual",
            "metadata": {},
        },
        {
            "name": "Toma de Presión",
            "price": 0.00,
            "description": "Control de presión arterial",
            "metadata": {},
        },
        {
            "name": "Curación Menor",
            "price": 0.00,
            "description": "Limpieza y vendaje de heridas",
            "metadata": {},
        },
        {
            "name": "Inyección",
            "price": 0.00,
            "description": "Aplicación de medicamentos (no incluye medicina)",
            "metadata": {},
        },
        {
            "name": "Certificado de Salud",
            "price": 0.00,
            "description": "Evaluación para estudios o trabajo",
            "metadata": {},
        },
        {
            "name": "Consulta Especialidad",
            "price": 0.00,
            "description": "Valoración especializada",
            "metadata": {},
        },
    ],
    "beauty": [
        {
            "name": "Corte de Cabello",
            "price": 0.00,
            "description": "Corte para hombre o mujer",
            "metadata": {},
        },
        {
            "name": "Manicure",
            "price": 0.00,
            "description": "Arreglo de uñas de manos",
            "metadata": {},
        },
        {
            "name": "Pedicure",
            "price": 0.00,
            "description": "Arreglo de uñas de pies",
            "metadata": {},
        },
        {
            "name": "Tinturarse",
            "price": 0.00,
            "description": "Tinte de cabello color completo",
            "metadata": {},
        },
        {
            "name": "Peinado",
            "price": 0.00,
            "description": "Peinado para ocasión especial",
            "metadata": {},
        },
        {
            "name": "Maquillaje",
            "price": 0.00,
            "description": "Maquillaje profesional",
            "metadata": {},
        },
        {
            "name": "Depilación",
            "price": 0.00,
            "description": "Depilación facial o corporal",
            "metadata": {},
        },
        {
            "name": "Alisado",
            "price": 0.00,
            "description": "Tratamiento de alisado permanente",
            "metadata": {},
        },
        {
            "name": "Tratamiento Capilar",
            "price": 0.00,
            "description": "Hidratación profunda",
            "metadata": {},
        },
        {
            "name": "Barba",
            "price": 0.00,
            "description": "Alineación y corte de barba",
            "metadata": {},
        },
    ],
    "default": [
        {
            "name": "Producto/Servicio 1",
            "price": 0.00,
            "description": "Descripción básica",
            "metadata": {},
        },
        {
            "name": "Producto/Servicio 2",
            "price": 0.00,
            "description": "Descripción básica",
            "metadata": {},
        },
        {
            "name": "Producto/Servicio 3",
            "price": 0.00,
            "description": "Descripción básica",
            "metadata": {},
        },
    ],
    "retail": [
        {
            "name": "Camiseta Básica",
            "price": 0.00,
            "description": "Tallas S, M, L, XL",
            "metadata": {},
        },
        {
            "name": "Pantalón Jean",
            "price": 0.00,
            "description": "Varias tallas y modelos",
            "metadata": {},
        },
        {
            "name": "Zapatos Deportivos",
            "price": 0.00,
            "description": "Zapatos cómodos para el día a día",
            "metadata": {},
        },
        {
            "name": "Chompa / Abrigo",
            "price": 0.00,
            "description": "Chompa abrigada",
            "metadata": {},
        },
        {
            "name": "Accesorios (Gorra/Cinturón)",
            "price": 0.00,
            "description": "Accesorios de moda",
            "metadata": {},
        },
    ],
    "groceries": [
        {
            "name": "Arroz 1kg",
            "price": 0.00,
            "description": "Arroz blanco de primera",
            "metadata": {},
        },
        {
            "name": "Aceite 1L",
            "price": 0.00,
            "description": "Aceite vegetal",
            "metadata": {},
        },
        {
            "name": "Huevos (Cubeta)",
            "price": 0.00,
            "description": "Cubeta de 30 huevos",
            "metadata": {},
        },
        {
            "name": "Leche 1L",
            "price": 0.00,
            "description": "Leche entera en funda o cartón",
            "metadata": {},
        },
        {
            "name": "Pan",
            "price": 0.00,
            "description": "Pan fresco del día",
            "metadata": {},
        },
    ],
    "tech": [
        {
            "name": "Cable USB/Cargador",
            "price": 0.00,
            "description": "Cable de carga rápida",
            "metadata": {},
        },
        {
            "name": "Audífonos Bluetooth",
            "price": 0.00,
            "description": "Audífonos inalámbricos",
            "metadata": {},
        },
        {
            "name": "Mica de Vidrio",
            "price": 0.00,
            "description": "Protector de pantalla para celular",
            "metadata": {},
        },
        {
            "name": "Estuche / Case",
            "price": 0.00,
            "description": "Protector anti-caídas",
            "metadata": {},
        },
        {
            "name": "Reparación Básica",
            "price": 0.00,
            "description": "Revisión y mantenimiento de celular",
            "metadata": {},
        },
    ],
    "services": [
        {
            "name": "Visita Técnica",
            "price": 0.00,
            "description": "Inspección y diagnóstico",
            "metadata": {},
        },
        {
            "name": "Mantenimiento Preventivo",
            "price": 0.00,
            "description": "Limpieza y ajustes básicos",
            "metadata": {},
        },
        {
            "name": "Reparación General",
            "price": 0.00,
            "description": "Mano de obra",
            "metadata": {},
        },
        {
            "name": "Instalación",
            "price": 0.00,
            "description": "Servicio de instalación de equipos",
            "metadata": {},
        },
        {
            "name": "Consultoría / Asesoría",
            "price": 0.00,
            "description": "Hora de asesoramiento profesional",
            "metadata": {},
        },
    ],
    "pharmacy": [
        {
            "name": "Paracetamol / Ibuprofeno",
            "price": 0.00,
            "description": "Analgésico básico",
            "metadata": {},
        },
        {
            "name": "Vitamina C",
            "price": 0.00,
            "description": "Suplemento vitamínico",
            "metadata": {},
        },
        {
            "name": "Alcohol Antiséptico",
            "price": 0.00,
            "description": "Frasco de 500ml",
            "metadata": {},
        },
        {
            "name": "Mascarillas",
            "price": 0.00,
            "description": "Caja de mascarillas desechables",
            "metadata": {},
        },
        {
            "name": "Crema Corporal",
            "price": 0.00,
            "description": "Cuidado personal",
            "metadata": {},
        },
    ],
    "hardware": [
        {
            "name": "Cemento (Saco)",
            "price": 0.00,
            "description": "Saco de cemento 50kg",
            "metadata": {},
        },
        {
            "name": "Pintura (Galón)",
            "price": 0.00,
            "description": "Galón de pintura interior/exterior",
            "metadata": {},
        },
        {
            "name": "Clavos / Tornillos",
            "price": 0.00,
            "description": "Por libra o docena",
            "metadata": {},
        },
        {
            "name": "Tubos PVC",
            "price": 0.00,
            "description": "Tubería estándar",
            "metadata": {},
        },
        {
            "name": "Herramienta Manual",
            "price": 0.00,
            "description": "Martillo, destornillador, etc.",
            "metadata": {},
        },
    ],
    "cbd": [
        {
            "name": "Aceite de CBD 500mg",
            "price": 0.00,
            "description": "Gotero 30ml, espectro completo",
            "metadata": {},
        },
        {
            "name": "Aceite de CBD 1000mg",
            "price": 0.00,
            "description": "Gotero 30ml, alta concentración",
            "metadata": {},
        },
        {
            "name": "Gomitas de CBD",
            "price": 0.00,
            "description": "Frasco de 30 gomitas relajantes",
            "metadata": {},
        },
        {
            "name": "Bálsamo Muscular CBD",
            "price": 0.00,
            "description": "Crema para alivio de dolor articular",
            "metadata": {},
        },
        {
            "name": "Flores Aromáticas CBD",
            "price": 0.00,
            "description": "1 gramo, cepa relajante (Uso legal EC)",
            "metadata": {},
        },
    ],
}


# Allowed archetypes
ALLOWED_ARCHETYPES = set(PRESETS.keys())

# ID validation patterns (Ecuador)
ID_PATTERNS = {
    "ruc": re.compile(r"^\d{13}$"),
    "cedula": re.compile(r"^\d{10}$"),
    "passport": re.compile(r"^[A-Z0-9]{6,20}$"),
}


def _sanitize_text(text: str | None) -> str:
    """Strip HTML tags and normalize text to prevent stored XSS."""
    if not text:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", "", str(text))
    # Escape any remaining HTML entities
    return html.escape(cleaned)


def _validate_whatsapp_number(num: str) -> bool:
    """Basic E.164-like validation for Ecuador/WhatsApp numbers."""
    if not num:
        return False
    # Remove common prefixes and non-digits for lenient check
    digits = re.sub(r"\D", "", num)
    # Ecuador mobile: 09xxxxxxxx (10 digits) or +5939xxxxxxxx (12 digits)
    # International: min 8, max 15 digits
    return 8 <= len(digits) <= 15


def _validate_url(url: str) -> bool:
    """Basic URL validation."""
    if not url:
        return True  # Optional field
    pattern = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
    return bool(pattern.match(url))


class AvenderOnboardingHandler(ApiHandler):
    """
    Handles the submission from the Onboarding Wizard.
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
            # 1. Atomic gate: reject if onboarding already completed
            if is_onboarding_complete():
                return {
                    "ok": False,
                    "error": "Onboarding already completed. Use the admin panel to modify settings.",
                }

            # 2. Validate required fields
            required_fields = [
                "idType",
                "idNumber",
                "tradeName",
                "archetype",
                "whatsappNumber",
                "adminPassword",
            ]
            missing = [f for f in required_fields if not input.get(f)]
            if missing:
                return {
                    "ok": False,
                    "error": f"Faltan campos obligatorios: {', '.join(missing)}",
                }

            # 3. Server-side input validation
            id_type = str(input.get("idType", "")).lower()
            id_number = str(input.get("idNumber", "")).strip()
            trade_name = str(input.get("tradeName", "")).strip()
            legal_name = str(input.get("legalName", "")).strip()
            whatsapp_number = str(input.get("whatsappNumber", "")).strip()
            admin_password = str(input.get("adminPassword", ""))
            archetype = str(input.get("archetype", "")).lower()
            payment_url = str(input.get("paymentUrl", "")).strip()

            # ID type validation
            if id_type not in ID_PATTERNS:
                return {
                    "ok": False,
                    "error": f"Tipo de ID no válido: {id_type}. Use: ruc, cedula, passport.",
                }
            if not ID_PATTERNS[id_type].match(id_number):
                return {"ok": False, "error": f"Número de {id_type} no válido."}

            # Trade name length
            if len(trade_name) < 2 or len(trade_name) > 200:
                return {
                    "ok": False,
                    "error": "El nombre comercial debe tener entre 2 y 200 caracteres.",
                }

            # WhatsApp number validation
            if not _validate_whatsapp_number(whatsapp_number):
                return {"ok": False, "error": "Número de WhatsApp no válido."}

            # Password validation
            if len(admin_password) < 8:
                return {
                    "ok": False,
                    "error": "La contraseña de administrador debe tener al menos 8 caracteres.",
                }

            # Archetype validation
            if archetype not in ALLOWED_ARCHETYPES:
                return {"ok": False, "error": f"Arquetipo no válido: {archetype}"}

            # Payment URL validation
            if payment_url and not _validate_url(payment_url):
                return {"ok": False, "error": "URL de pago no válida."}

            # Catalog items validation
            catalog_items = input.get("catalogItems", [])
            if isinstance(catalog_items, list) and len(catalog_items) > 500:
                return {
                    "ok": False,
                    "error": "No puedes agregar más de 500 productos al catálogo.",
                }

            # Allowed numbers validation
            restrict_access = input.get("restrictAccess", False)
            allowed_numbers = input.get("allowedNumbers", "")
            if restrict_access and allowed_numbers:
                numbers_list = [
                    n.strip() for n in str(allowed_numbers).split(",") if n.strip()
                ]
                if len(numbers_list) > 100:
                    return {
                        "ok": False,
                        "error": "No puedes agregar más de 100 números permitidos.",
                    }

            # 4. Sanitize all text inputs to prevent stored XSS
            input["tradeName"] = _sanitize_text(trade_name)
            input["legalName"] = _sanitize_text(legal_name)
            input["policies"] = _sanitize_text(input.get("policies"))
            input["promotions"] = _sanitize_text(input.get("promotions"))
            input["deliveryRules"] = _sanitize_text(input.get("deliveryRules"))
            input["agentName"] = _sanitize_text(input.get("agentName"))

            # Sanitize catalog items
            if isinstance(catalog_items, list):
                for item in catalog_items:
                    if isinstance(item, dict):
                        item["name"] = _sanitize_text(item.get("name"))
                        item["description"] = _sanitize_text(item.get("description"))

            # 5. Start SQLite transaction
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")

            # Double-check atomic gate inside transaction
            cursor.execute(
                "SELECT 1 FROM tenant_config WHERE key = 'onboarding_complete' AND value = 'true'"
            )
            if cursor.fetchone():
                conn.rollback()
                conn.close()
                return {"ok": False, "error": "Onboarding already completed."}

            # 6. Save normalized wizard data
            normalized = normalize_settings(input)
            for key, value in normalized.items():
                val_str = (
                    json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                )
                cursor.execute(
                    "INSERT INTO tenant_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, val_str),
                )

            # 7. Store admin password inside this transaction. Opening a second
            # SQLite write connection here would deadlock against BEGIN IMMEDIATE.
            cursor.execute(
                "INSERT INTO tenant_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (PASSWORD_KEY, hash_admin_password(admin_password)),
            )

            # 8. Configure WhatsApp
            self._configure_whatsapp(normalized)

            # 9. Handle catalog items — only clear if we have new items
            if catalog_items and len(catalog_items) > 0:
                cursor.execute("DELETE FROM catalog_item")
                PrintStyle.info(
                    f"Avender: Saving {len(catalog_items)} verified catalog items."
                )
                for item in catalog_items:
                    name = item.get("name", "Sin nombre") or "Sin nombre"
                    price = float(item.get("price", 0.0) or 0.0)
                    desc = item.get("description", "")
                    meta_str = json.dumps(item.get("metadata", {}))
                    cursor.execute(
                        "INSERT INTO catalog_item (name, price, description, metadata) VALUES (?, ?, ?, ?)",
                        (name, price, desc, meta_str),
                    )
            else:
                # Only clear and inject presets if table is empty
                cursor.execute("SELECT COUNT(*) FROM catalog_item")
                count = cursor.fetchone()[0]
                if count == 0:
                    PrintStyle.info(
                        f"Avender: Injecting catalog presets for archetype '{archetype}'"
                    )
                    preset_items = PRESETS.get(archetype, PRESETS["default"])
                    for item in preset_items:
                        meta_str = json.dumps(item.get("metadata", {}))
                        cursor.execute(
                            "INSERT INTO catalog_item (name, price, description, metadata) VALUES (?, ?, ?, ?)",
                            (
                                item.get("name"),
                                item.get("price", 0.0),
                                item.get("description"),
                                meta_str,
                            ),
                        )
                    PrintStyle.success(
                        f"Avender: Injected {len(preset_items)} preset items."
                    )

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

    def _configure_whatsapp(self, settings: dict) -> None:
        config = plugins.get_plugin_config("_whatsapp_integration") or {}
        allowed_numbers = []
        if settings.get("restrict_access"):
            allowed_numbers = sorted(
                normalize_allowed_numbers(settings.get("allowed_numbers", ""))
            )
        config.update(
            {
                "enabled": True,
                "mode": config.get("mode", "dedicated"),
                "allowed_numbers": allowed_numbers,
                "agent_profile": "avender_sales",
            }
        )
        plugins.save_plugin_config("_whatsapp_integration", "", "", config)
