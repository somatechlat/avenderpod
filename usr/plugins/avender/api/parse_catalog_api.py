"""
Avender Catalog Parse API — thin HTTP wrapper around CatalogEngine.
Route: /api/plugins/avender/parse_catalog_api
"""

from helpers.api import ApiHandler, Request, Response
from helpers.print_style import PrintStyle
from usr.plugins.avender.helpers.catalog_engine import CatalogEngine
from usr.plugins.avender.helpers.setup_auth import require_setup_token_until_onboarded
import os
import base64
import tempfile


class ParseCatalogHandler(ApiHandler):
    """Handles catalog file uploads from the onboarding wizard."""

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        setup_error = require_setup_token_until_onboarded(input, request)
        if setup_error:
            return setup_error

        tmp_path = None
        try:
            catalog_file = input.get("catalogFile")
            if not catalog_file:
                return {"ok": False, "error": "No catalog file provided."}

            name = catalog_file.get("name", "")
            b64_content = catalog_file.get("content", "")
            if "," in b64_content:
                b64_content = b64_content.split(",", 1)[1]

            approx_size = len(b64_content) * 0.75
            if approx_size > 26_214_400:
                return {"ok": False, "error": "El archivo es demasiado grande. El límite es de 25 MB."}

            ext = os.path.splitext(name)[1].lower()
            allowed = (".png", ".jpg", ".jpeg", ".pdf", ".xls", ".xlsx", ".doc", ".docx", ".txt", ".csv")
            if ext not in allowed:
                return {"ok": False, "error": "Tipo de archivo no permitido."}

            file_bytes = base64.b64decode(b64_content)
            tmp_dir = "/a0/tmp" if os.path.isdir("/a0/tmp") and os.access("/a0/tmp", os.W_OK) else tempfile.gettempdir()
            os.makedirs(tmp_dir, exist_ok=True)
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=tmp_dir)
            try:
                with os.fdopen(tmp_fd, "wb") as f:
                    f.write(file_bytes)
            except Exception:
                os.close(tmp_fd)
                raise

            image_b64 = None
            image_mime = None
            if ext in (".png", ".jpg", ".jpeg"):
                image_b64 = b64_content
                image_mime = f"image/{ext[1:]}"

            archetype = str(input.get("archetype") or "restaurant").lower()

            context = self.use_context("parse_catalog")
            agent = context.agent0 if context else None

            engine = CatalogEngine(agent=agent)
            result = await engine.parse_file(
                file_path=tmp_path,
                file_name=name,
                image_b64=image_b64,
                image_mime=image_mime,
                archetype=archetype,
                store_in_memory=False,  # Onboarding handles persistence separately
            )

            items = result.get("items", [])
            if not items:
                return {
                    "ok": False,
                    "error": (
                        "No se detectaron productos con suficiente claridad en el archivo. "
                        "Prueba con una imagen/PDF más nítido o usa CSV/XLSX con columnas de producto y precio."
                    ),
                }

            return {"ok": True, "items": items}

        except Exception as e:
            PrintStyle.error(f"Error parsing catalog: {e}")
            return {"ok": False, "error": "Error procesando el catálogo. Por favor intenta con otro archivo."}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
