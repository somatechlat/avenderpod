from helpers.api import ApiHandler, Request, Response
from helpers.print_style import PrintStyle
from langchain_core.messages import HumanMessage
import json
import os
import base64
import uuid

class ParseCatalogHandler(ApiHandler):
    """
    Parses a catalog file dynamically via Vision AI or text extraction.
    Route: /api/plugins/avender/parse_catalog
    """

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            catalog_file = input.get("catalogFile")
            if not catalog_file:
                return {"ok": False, "error": "No catalog file provided."}

            name = catalog_file.get("name", "")
            b64_content = catalog_file.get("content", "")
            
            if "," in b64_content:
                b64_content = b64_content.split(",", 1)[1]
            
            # 1. Enforce max file size: 100MB (approximate using base64 length)
            # Base64 length * 0.75 gives approximate bytes. 100MB = 104,857,600 bytes.
            approx_size = len(b64_content) * 0.75
            if approx_size > 104_857_600:
                return {"ok": False, "error": "El archivo es demasiado grande. El límite es de 100 MB."}
                
            ext = os.path.splitext(name)[1].lower()
            
            # 2. Strict whitelist of allowed extensions (no zip allowed, no code injection)
            allowed_extensions = [".png", ".jpg", ".jpeg", ".pdf", ".xls", ".xlsx", ".doc", ".docx", ".txt", ".csv"]
            if ext not in allowed_extensions or ext == ".zip":
                return {"ok": False, "error": f"Tipo de archivo no permitido. Solo se permiten imágenes, PDF, Excel, Word y texto plano."}

            file_bytes = base64.b64decode(b64_content)
            
            catalog_data = ""
            image_b64 = None
            image_mime = None
            
            if ext in [".png", ".jpg", ".jpeg"]:
                image_b64 = b64_content
                image_mime = f"image/{ext[1:]}"
            else:
                temp_path = f"/a0/tmp/{uuid.uuid4()}{ext}"
                os.makedirs("/a0/tmp", exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(file_bytes)
                
                text = ""
                if ext == ".pdf":
                    try:
                        import fitz
                        doc = fitz.open(temp_path)
                        text = "\n".join([page.get_text() for page in doc])
                    except ImportError:
                        PrintStyle.error("PyMuPDF (fitz) is not installed.")
                elif ext in [".xls", ".xlsx"]:
                    try:
                        import pandas as pd
                        text = pd.read_excel(temp_path).to_csv(index=False)
                    except ImportError:
                        PrintStyle.error("Pandas or openpyxl is not installed.")
                else:
                    with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                
                if text:
                    # Limit text to 20,000 characters to avoid breaking the LLM context window
                    catalog_data = text[:20000]
                    if len(text) > 20000:
                        PrintStyle.warning(f"Catalog text truncated from {len(text)} to 20000 chars.")
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)

            context = self.use_context("parse_catalog")
            model = context.agent.get_utility_model()
            
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
                content_list.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_mime};base64,{image_b64}"}
                })
            if not content_list:
                return {"ok": False, "error": "No se pudo extraer contenido del archivo."}
            
            PrintStyle.info("Parsing catalog...")
            llm_resp, _ = await model.unified_call(
                system_message=sys_prompt,
                messages=[HumanMessage(content=content_list)]
            )
            
            import re
            match = re.search(r'\[\s*\{.*\}\s*\]', llm_resp, re.DOTALL)
            if match:
                clean_json = match.group(0)
            else:
                clean_json = llm_resp.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()

            items = json.loads(clean_json)

            if not isinstance(items, list):
                raise ValueError("El modelo no retornó una lista JSON.")

            return {"ok": True, "items": items}
            
        except Exception as e:
            PrintStyle.error(f"Error parsing catalog: {e}")
            return {"ok": False, "error": str(e)}
