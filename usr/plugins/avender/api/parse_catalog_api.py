from helpers.api import ApiHandler, Request, Response
from helpers.print_style import PrintStyle
from langchain_core.messages import HumanMessage
import json
import os
import base64
import re
import tempfile
from typing import Any


class ParseCatalogHandler(ApiHandler):
    """
    Parses a catalog file dynamically via Vision AI or text extraction.
    Route: /api/plugins/avender/parse_catalog
    """

    @classmethod
    def requires_auth(cls) -> bool:
        # Require auth to prevent unauthorized LLM credit burning
        return True

    @classmethod
    def requires_csrf(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> dict | Response:
        tmp_path = None
        try:
            catalog_file = input.get("catalogFile")
            if not catalog_file:
                return {"ok": False, "error": "No catalog file provided."}

            name = catalog_file.get("name", "")
            b64_content = catalog_file.get("content", "")

            if "," in b64_content:
                b64_content = b64_content.split(",", 1)[1]

            # 1. Enforce max file size: 25MB (approximate using base64 length)
            approx_size = len(b64_content) * 0.75
            if approx_size > 26_214_400:  # 25MB
                return {
                    "ok": False,
                    "error": "El archivo es demasiado grande. El límite es de 25 MB.",
                }

            ext = os.path.splitext(name)[1].lower()

            # 2. Strict whitelist of allowed extensions
            allowed_extensions = [
                ".png",
                ".jpg",
                ".jpeg",
                ".pdf",
                ".xls",
                ".xlsx",
                ".doc",
                ".docx",
                ".txt",
                ".csv",
            ]
            if ext not in allowed_extensions:
                return {
                    "ok": False,
                    "error": "Tipo de archivo no permitido. Solo se permiten imágenes, PDF, Excel, Word y texto plano.",
                }

            file_bytes = base64.b64decode(b64_content)

            catalog_data = ""
            image_b64 = None
            image_mime = None

            if ext in [".png", ".jpg", ".jpeg"]:
                image_b64 = b64_content
                image_mime = f"image/{ext[1:]}"
            else:
                # Use a proper temp file with cleanup
                os.makedirs("/a0/tmp", exist_ok=True)
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext, dir="/a0/tmp")
                try:
                    with os.fdopen(tmp_fd, "wb") as f:
                        f.write(file_bytes)
                except Exception:
                    os.close(tmp_fd)
                    raise

                text = ""
                if ext == ".pdf":
                    try:
                        import fitz

                        doc = fitz.open(tmp_path)
                        text = "\n".join(
                            [page.get_text() for page in doc]  # type: ignore[attr-defined]
                        )
                    except ImportError:
                        PrintStyle.error("PyMuPDF (fitz) is not installed.")
                elif ext in [".xls", ".xlsx"]:
                    try:
                        import pandas as pd

                        text = pd.read_excel(tmp_path).to_csv(index=False)
                    except ImportError:
                        PrintStyle.error("Pandas or openpyxl is not installed.")
                else:
                    with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()

                if text:
                    catalog_data = text[:20000]
                    if len(text) > 20000:
                        PrintStyle.warning(
                            f"Catalog text truncated from {len(text)} to 20000 chars."
                        )

            context = self.use_context("parse_catalog")
            agent = context.agent0
            model = agent.get_utility_model()
            if model is None:
                fallback_items = self._fallback_parse_catalog(catalog_data)
                if fallback_items:
                    return {"ok": True, "items": fallback_items}
                return {
                    "ok": False,
                    "error": "No hay modelo de utilidad configurado para procesar el catálogo.",
                }
            model_client: Any = model

            sys_prompt = (
                "Eres un experto extractor de datos. Convierte el siguiente texto/CSV o IMAGEN cruda de un menú/catálogo "
                "en un array JSON de objetos. Cada objeto DEBE tener las siguientes claves obligatorias: "
                "'name' (string), 'description' (string, breve), 'price' (número flotante, extrae solo el valor numérico), "
                "y 'metadata' (un objeto JSON que contenga cualquier otra columna o información extra relevante). "
                "Si ves una foto de un menú, extrae los platillos y precios. "
                "RETORNA SOLAMENTE JSON VÁLIDO. NADA MÁS."
            )

            content_list = []
            if catalog_data:
                content_list.append({"type": "text", "text": catalog_data})
            if image_b64:
                content_list.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{image_mime};base64,{image_b64}"},
                    }
                )
            if not content_list:
                return {
                    "ok": False,
                    "error": "No se pudo extraer contenido del archivo.",
                }

            PrintStyle.info("Parsing catalog...")
            try:
                llm_resp, _ = await model_client.unified_call(
                    system_message=sys_prompt,
                    messages=[HumanMessage(content=content_list)],
                )

                # Robust JSON extraction
                items = self._extract_json_items(llm_resp)
                if not isinstance(items, list):
                    raise ValueError("El modelo no retornó una lista JSON.")
            except Exception as model_error:
                PrintStyle.warning(
                    f"Catalog model parsing failed, using fallback: {model_error}"
                )
                fallback_items = self._fallback_parse_catalog(catalog_data)
                if not fallback_items:
                    raise
                items = fallback_items

            return {"ok": True, "items": items}

        except Exception as e:
            PrintStyle.error(f"Error parsing catalog: {e}")
            return {
                "ok": False,
                "error": "Error procesando el catálogo. Por favor intenta con otro archivo o formato.",
            }
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _extract_json_items(self, llm_resp: str):
        """Robustly extract a JSON array from LLM response with multiple fallback strategies."""
        # Strategy 1: Regex search for JSON array
        match = re.search(r"\[\s*\{.*\}\s*\]", llm_resp, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # Strategy 2: Strip markdown code fences and try full response
        clean = llm_resp.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass

        # Strategy 3: Find first [ and last ]
        start = clean.find("[")
        end = clean.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(clean[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError("No se pudo extraer JSON válido de la respuesta del modelo.")

    def _fallback_parse_catalog(self, catalog_data: str) -> list[dict[str, Any]]:
        """Deterministic parser used when model output is unavailable or malformed."""
        if not catalog_data:
            return []

        lines = [line.strip() for line in catalog_data.splitlines() if line.strip()]
        price_pattern = re.compile(r"(\d+(?:[.,]\d{1,2})?)")
        items: list[dict[str, Any]] = []

        for line in lines:
            if len(items) >= 200:
                break

            price_match = price_pattern.search(line)
            if not price_match:
                continue

            raw_price = price_match.group(1).replace(",", ".")
            try:
                price = float(raw_price)
            except ValueError:
                continue

            # Split name/description around likely separators.
            name_part = line[: price_match.start()].strip(" -:\t")
            desc_part = line[price_match.end() :].strip(" -:\t")

            if not name_part:
                continue

            items.append(
                {
                    "name": name_part[:160],
                    "description": desc_part[:400],
                    "price": price,
                    "metadata": {"source": "fallback_text_parser"},
                }
            )

        return items
