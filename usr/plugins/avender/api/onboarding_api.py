from helpers.api import ApiHandler, Request, Response
from helpers.print_style import PrintStyle
from usr.plugins.avender.helpers.db import save_tenant_config, get_tenant_config, get_connection
import json
import os
import traceback

PRESETS = {
    "restaurant": [
        {"name": "Hamburguesa Clásica", "price": 0.00, "description": "Hamburguesa con queso, lechuga y tomate", "metadata": {}},
        {"name": "Papas Fritas", "price": 0.00, "description": "Porción de papas fritas crujientes", "metadata": {}},
        {"name": "Gaseosa", "price": 0.00, "description": "Bebida carbonatada 500ml", "metadata": {}},
        {"name": "Pizza Personal", "price": 0.00, "description": "Pizza de 4 porciones", "metadata": {}},
        {"name": "Almuerzo Ejecutivo", "price": 0.00, "description": "Sopa, plato fuerte y jugo", "metadata": {}},
        {"name": "Tacos", "price": 0.00, "description": "Orden de 3 tacos", "metadata": {}},
        {"name": "Ensalada César", "price": 0.00, "description": "Ensalada fresca con pollo", "metadata": {}},
        {"name": "Jugo Natural", "price": 0.00, "description": "Jugo de frutas de temporada", "metadata": {}},
        {"name": "Postre del Día", "price": 0.00, "description": "Postre dulce", "metadata": {}},
        {"name": "Café", "price": 0.00, "description": "Café pasado o americano", "metadata": {}}
    ],
    "liquor": [
        {"name": "Cerveza Nacional", "price": 0.00, "description": "Botella de cerveza 600ml", "metadata": {}},
        {"name": "Vino Tinto", "price": 0.00, "description": "Botella de vino tinto joven", "metadata": {}},
        {"name": "Ron", "price": 0.00, "description": "Botella de ron añejo 750ml", "metadata": {}},
        {"name": "Vodka", "price": 0.00, "description": "Botella de vodka 750ml", "metadata": {}},
        {"name": "Whisky", "price": 0.00, "description": "Botella de whisky 12 años", "metadata": {}},
        {"name": "Hielo", "price": 0.00, "description": "Funda de hielo en cubos", "metadata": {}},
        {"name": "Agua Mineral", "price": 0.00, "description": "Agua con gas 1.5L", "metadata": {}},
        {"name": "Gaseosa Cola", "price": 0.00, "description": "Bebida cola 3L", "metadata": {}},
        {"name": "Snacks", "price": 0.00, "description": "Papas fritas o nachos de funda", "metadata": {}},
        {"name": "Cigarrillos", "price": 0.00, "description": "Cajetilla de 20 unidades", "metadata": {}}
    ],
    "doctor": [
        {"name": "Consulta General", "price": 0.00, "description": "Valoración médica inicial", "metadata": {}},
        {"name": "Control", "price": 0.00, "description": "Cita de seguimiento", "metadata": {}},
        {"name": "Certificado Médico", "price": 0.00, "description": "Emisión de certificado", "metadata": {}},
        {"name": "Lectura de Exámenes", "price": 0.00, "description": "Revisión de resultados de laboratorio", "metadata": {}},
        {"name": "Telemedicina", "price": 0.00, "description": "Consulta médica virtual", "metadata": {}},
        {"name": "Toma de Presión", "price": 0.00, "description": "Control de presión arterial", "metadata": {}},
        {"name": "Curación Menor", "price": 0.00, "description": "Limpieza y vendaje de heridas", "metadata": {}},
        {"name": "Inyección", "price": 0.00, "description": "Aplicación de medicamentos (no incluye medicina)", "metadata": {}},
        {"name": "Certificado de Salud", "price": 0.00, "description": "Evaluación para estudios o trabajo", "metadata": {}},
        {"name": "Consulta Especialidad", "price": 0.00, "description": "Valoración especializada", "metadata": {}}
    ],
    "beauty": [
        {"name": "Corte de Cabello", "price": 0.00, "description": "Corte para hombre o mujer", "metadata": {}},
        {"name": "Manicure", "price": 0.00, "description": "Arreglo de uñas de manos", "metadata": {}},
        {"name": "Pedicure", "price": 0.00, "description": "Arreglo de uñas de pies", "metadata": {}},
        {"name": "Tinturarse", "price": 0.00, "description": "Tinte de cabello color completo", "metadata": {}},
        {"name": "Peinado", "price": 0.00, "description": "Peinado para ocasión especial", "metadata": {}},
        {"name": "Maquillaje", "price": 0.00, "description": "Maquillaje profesional", "metadata": {}},
        {"name": "Depilación", "price": 0.00, "description": "Depilación facial o corporal", "metadata": {}},
        {"name": "Alisado", "price": 0.00, "description": "Tratamiento de alisado permanente", "metadata": {}},
        {"name": "Tratamiento Capilar", "price": 0.00, "description": "Hidratación profunda", "metadata": {}},
        {"name": "Barba", "price": 0.00, "description": "Alineación y corte de barba", "metadata": {}}
    ],
    "default": [
        {"name": "Producto/Servicio 1", "price": 0.00, "description": "Descripción básica", "metadata": {}},
        {"name": "Producto/Servicio 2", "price": 0.00, "description": "Descripción básica", "metadata": {}},
        {"name": "Producto/Servicio 3", "price": 0.00, "description": "Descripción básica", "metadata": {}}
    ],
    "retail": [
        {"name": "Camiseta Básica", "price": 0.00, "description": "Tallas S, M, L, XL", "metadata": {}},
        {"name": "Pantalón Jean", "price": 0.00, "description": "Varias tallas y modelos", "metadata": {}},
        {"name": "Zapatos Deportivos", "price": 0.00, "description": "Zapatos cómodos para el día a día", "metadata": {}},
        {"name": "Chompa / Abrigo", "price": 0.00, "description": "Chompa abrigada", "metadata": {}},
        {"name": "Accesorios (Gorra/Cinturón)", "price": 0.00, "description": "Accesorios de moda", "metadata": {}}
    ],
    "groceries": [
        {"name": "Arroz 1kg", "price": 0.00, "description": "Arroz blanco de primera", "metadata": {}},
        {"name": "Aceite 1L", "price": 0.00, "description": "Aceite vegetal", "metadata": {}},
        {"name": "Huevos (Cubeta)", "price": 0.00, "description": "Cubeta de 30 huevos", "metadata": {}},
        {"name": "Leche 1L", "price": 0.00, "description": "Leche entera en funda o cartón", "metadata": {}},
        {"name": "Pan", "price": 0.00, "description": "Pan fresco del día", "metadata": {}}
    ],
    "tech": [
        {"name": "Cable USB/Cargador", "price": 0.00, "description": "Cable de carga rápida", "metadata": {}},
        {"name": "Audífonos Bluetooth", "price": 0.00, "description": "Audífonos inalámbricos", "metadata": {}},
        {"name": "Mica de Vidrio", "price": 0.00, "description": "Protector de pantalla para celular", "metadata": {}},
        {"name": "Estuche / Case", "price": 0.00, "description": "Protector anti-caídas", "metadata": {}},
        {"name": "Reparación Básica", "price": 0.00, "description": "Revisión y mantenimiento de celular", "metadata": {}}
    ],
    "services": [
        {"name": "Visita Técnica", "price": 0.00, "description": "Inspección y diagnóstico", "metadata": {}},
        {"name": "Mantenimiento Preventivo", "price": 0.00, "description": "Limpieza y ajustes básicos", "metadata": {}},
        {"name": "Reparación General", "price": 0.00, "description": "Mano de obra", "metadata": {}},
        {"name": "Instalación", "price": 0.00, "description": "Servicio de instalación de equipos", "metadata": {}},
        {"name": "Consultoría / Asesoría", "price": 0.00, "description": "Hora de asesoramiento profesional", "metadata": {}}
    ],
    "pharmacy": [
        {"name": "Paracetamol / Ibuprofeno", "price": 0.00, "description": "Analgésico básico", "metadata": {}},
        {"name": "Vitamina C", "price": 0.00, "description": "Suplemento vitamínico", "metadata": {}},
        {"name": "Alcohol Antiséptico", "price": 0.00, "description": "Frasco de 500ml", "metadata": {}},
        {"name": "Mascarillas", "price": 0.00, "description": "Caja de mascarillas desechables", "metadata": {}},
        {"name": "Crema Corporal", "price": 0.00, "description": "Cuidado personal", "metadata": {}}
    ],
    "hardware": [
        {"name": "Cemento (Saco)", "price": 0.00, "description": "Saco de cemento 50kg", "metadata": {}},
        {"name": "Pintura (Galón)", "price": 0.00, "description": "Galón de pintura interior/exterior", "metadata": {}},
        {"name": "Clavos / Tornillos", "price": 0.00, "description": "Por libra o docena", "metadata": {}},
        {"name": "Tubos PVC", "price": 0.00, "description": "Tubería estándar", "metadata": {}},
        {"name": "Herramienta Manual", "price": 0.00, "description": "Martillo, destornillador, etc.", "metadata": {}}
    ]
}


class AvenderOnboardingHandler(ApiHandler):
    """
    Handles the submission from the Alpine.js Onboarding Wizard.
    Route: /api/plugins/avender/onboarding_api
    (Auto-resolved by helpers/api.py register_api_route → plugins/<plugin>/<handler>)
    """

    @classmethod
    def requires_auth(cls) -> bool:
        # Onboarding wizard is accessed before full auth is established.
        # The wizard itself is only served to users who have access to the
        # Agent Zero UI, so this is safe.
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            # 1. Reject if onboarding already completed (one-time wizard)
            existing = get_tenant_config("onboarding_complete")
            if existing == "true":
                return {"ok": False, "error": "Onboarding already completed. Use the admin panel to modify settings."}

            # 2. Validate required fields
            required_fields = ["idType", "idNumber", "tradeName", "archetype"]
            missing = [f for f in required_fields if not input.get(f)]
            if missing:
                return {"ok": False, "error": f"Missing required fields: {', '.join(missing)}"}

            # 3. Save all wizard data to tenant_config KV store
            save_tenant_config(input)

            catalog_items = input.get("catalogItems", [])
            archetype = input.get("archetype", "default")
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM catalog_item") # Clear previous if any

            if catalog_items and len(catalog_items) > 0:
                PrintStyle.info(f"Avender: Saving {len(catalog_items)} verified catalog items.")
                for item in catalog_items:
                    # In case user left fields empty
                    name = item.get('name', 'Sin nombre')
                    price = float(item.get('price', 0.0))
                    desc = item.get('description', '')
                    meta_str = json.dumps(item.get('metadata', {}))
                    
                    cursor.execute(
                        "INSERT INTO catalog_item (name, price, description, metadata) VALUES (?, ?, ?, ?)",
                        (name, price, desc, meta_str)
                    )
            else:
                # If no valid data was processed, inject presets
                PrintStyle.info(f"Avender: Injecting catalog presets for archetype '{archetype}'")
                preset_items = PRESETS.get(archetype, PRESETS["default"])
                for item in preset_items:
                    meta_str = json.dumps(item.get('metadata', {}))
                    cursor.execute(
                        "INSERT INTO catalog_item (name, price, description, metadata) VALUES (?, ?, ?, ?)",
                        (item.get('name'), item.get('price', 0.0), item.get('description'), meta_str)
                    )
                PrintStyle.success(f"Avender: Injected {len(preset_items)} preset items.")

            conn.commit()
            conn.close()

            # 5. Mark onboarding as complete
            save_tenant_config({"onboarding_complete": "true"})

            PrintStyle.success(
                f"Avender Onboarding: {input.get('tradeName')} ({input.get('idType')} {input.get('idNumber')}) — "
                f"Archetype: {input.get('archetype')}"
            )

            return {
                "ok": True,
                "message": "¡Configuración guardada exitosamente!",
                "tradeName": input.get("tradeName", ""),
                "archetype": input.get("archetype", ""),
            }

        except Exception as e:
            PrintStyle.error(f"Avender Onboarding Error: {e}")
            return {"ok": False, "error": str(e)}

