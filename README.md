# ¡A VENDER! — The Omni-Industry WhatsApp Sales Assistant

**¡A VENDER!** is a comprehensive, AI-driven SaaS platform that allows business owners (from restaurants to clinics and retail stores) to deploy an autonomous sales and customer service agent over WhatsApp. Built on top of the **Agent Zero** framework, it leverages state-of-the-art Large Language Models, Vision AI, and Whisper audio transcription to provide a "Zero-Friction" setup and robust, 24/7 autonomous operations.

## Key Features

- **Omni-Industry Archetypes:** Pre-configured workflows and presets for 10+ industries including Retail, Groceries, Medical, Services, Beauty, and more.
- **Zero-Friction Onboarding:** A stunning, simple UI wizard that handles legal data, delivery logic, payment methods (Cash, Transfer, Links), and Agent personality settings in plain language.
- **AI Catalog Ingestion:** Simply upload a photo of a menu, a PDF, or an Excel sheet. The Vision AI & NLP engine extracts the products and prices dynamically into a structured catalog for user verification.
- **Multimodal Interactions:** Fully supports WhatsApp voice notes (transcribed via a centralized Whisper server) and handles location coordinates.
- **Enterprise-Grade Security:**
  - Strict file-type and size validation (Max 100MB, no executables, no ZIPs).
  - WhatsApp number lockdown (Restrict the agent to only talk to a pre-defined list of up to 100 allowed numbers).
  - Built-in LOPDP (Ecuador) compliance via separated tenant state.

## Architecture & Technology Stack

¡A VENDER! operates as an "Agent Pod", deployed via Docker, encapsulating multiple services:
- **Core Orchestrator:** Agent Zero (Python) running custom `avender` plugins and extensions.
- **Frontend / UI:** Lit Web Components + TailwindCSS + LeafletJS (served via Python backend).
- **WhatsApp Bridge:** Native Baileys integration via Agent Zero's `_whatsapp_integration` plugin (port 3100 internal).
- **Audio Processing:** CPU-optimized Faster-Whisper server (port 45002).
- **SysAdmin Control Plane:** Django + Ninja (port 45000) for tenant lifecycle management.
- **LLM Provider:** Integration with OpenRouter (Nemotron 120B).

## Getting Started

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/somatechlat/avenderpod.git
   cd avenderpod
   ```

2. **Environment Configuration:**
   Configure your `.env` variables including your `OPENROUTER_API_KEY`, `VULTR_API_KEY`, and `DJANGO_SECRET_KEY`.

3. **Start the Platform:**
   Use the provided Docker Compose or run the python UI script directly for local development:
   ```bash
   python run_ui.py
   ```

4. **Access the Onboarding Wizard:**
   Navigate to the Avender Onboarding page to configure the agent instance and test the catalog ingestion features.

## Documentation

Full system architecture and requirements are detailed in the [Master SRS Document](docs/avender_srs_master.md).

## Credits

Developed by **[SomaTech](https://www.somatech.dev)**.  
Powered by **[Yachaq.ai](https://yachaq.ai)**.
