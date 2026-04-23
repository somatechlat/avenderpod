from helpers.api import ApiHandler, Request, Response
from helpers.print_style import PrintStyle
from agent import UserMessage
import base64
import os
import tempfile
import requests

class WizardChatHandler(ApiHandler):
    """
    Handles AI Copilot questions from the Onboarding Wizard.
    Route: /api/plugins/avender/wizard_chat
    """

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            question = input.get("question", "")
            file_data = input.get("file", None)
            
            attachments = []
            tmp_files_to_cleanup = []

            # Handle attachments
            if file_data and "content" in file_data and "name" in file_data:
                file_name = file_data["name"].lower()
                content_b64 = file_data["content"]
                
                # Strip the data URI scheme if present
                if "," in content_b64:
                    header, encoded = content_b64.split(",", 1)
                else:
                    header = "data:application/octet-stream;base64"
                    encoded = content_b64

                file_bytes = base64.b64decode(encoded)

                audio_exts = [".ogg", ".mp3", ".wav", ".m4a", ".webm", ".aac", ".oga"]
                is_audio = any(file_name.endswith(ext) for ext in audio_exts)
                
                if is_audio:
                    PrintStyle.info("Avender Wizard Chat: Processing audio via Whisper...")
                    # Send to Whisper
                    try:
                        mime_type = "audio/ogg" if file_name.endswith(".ogg") else "audio/mpeg"
                        whisper_res = requests.post(
                            "http://whisper_server:8000/v1/audio/transcriptions",
                            files={"file": (file_name, file_bytes, mime_type)},
                            data={"model": "whisper-1", "language": "es"},
                            timeout=45,
                        )
                        whisper_res.raise_for_status()
                        transcribed = whisper_res.json().get("text", "").strip()
                        question += f"\n[Transcripción de Audio del Usuario]: {transcribed}"
                        PrintStyle.success("Avender Wizard Chat: Audio transcribed successfully.")
                    except Exception as e:
                        PrintStyle.error(f"Whisper Transcription Error: {e}")
                        question += f"\n[Error: No se pudo transcribir el audio adjunto]"
                else:
                    # Treat as image or document for Agent Zero Vision
                    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1])
                    tmp_file.write(file_bytes)
                    tmp_file.close()
                    attachments.append(tmp_file.name)
                    tmp_files_to_cleanup.append(tmp_file.name)
                    PrintStyle.info(f"Avender Wizard Chat: Attached file {file_name}")

            if not question and not attachments:
                return {"ok": False, "error": "No question or file provided"}

            sys_prompt = (
                "IMPORTANTE INSTRUCCIÓN DE ROL: Eres el Copiloto de IA del asistente de enrolamiento de ¡A VENDER!, un SaaS de ventas por WhatsApp. "
                "Tu objetivo es ayudar a dueños de negocio (no técnicos, de 17 a 65 años) a llenar el formulario de configuración. "
                "Puedes usar todas tus herramientas para ayudarlos. Mantén tus respuestas extremadamente breves, claras y en lenguaje simple. "
                "Si te envían una foto de su menú, analízalo y ayúdales. "
                "No uses jerga técnica (nada de LLMs, embeddings, APIs). Responde en texto plano o markdown básico.\n\n"
            )
            
            full_question = sys_prompt + question
            
            # Use persistent context to allow memory and tools
            context = self.use_context("wizard_chat")
            
            PrintStyle.info(f"Avender Wizard Chat processing via Agent...")
            msg = UserMessage(message=full_question, attachments=attachments)
            task = context.communicate(msg)
            answer = await task.result()
            
            # Cleanup temp files
            for tmp_file in tmp_files_to_cleanup:
                try:
                    os.remove(tmp_file)
                except:
                    pass
            
            return {"ok": True, "answer": str(answer)}

        except Exception as e:
            PrintStyle.error(f"Wizard Chat Error: {e}")
            return {"ok": False, "error": str(e)}
