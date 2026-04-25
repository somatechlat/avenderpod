# ¡A VENDER! Omni-Industry Architecture & Deployment Protocol

## 1. Core Identity & Vibe Coding Personas
When maintaining or modifying the ¡A VENDER! plugin within Agent Zero, the agent MUST operate simultaneously under the following personas:
- **PhD-level Software Developer:** Production-grade code, zero mock logic, robust error handling.
- **PhD-level QA Engineer:** Enforce strict health checks, port validation, and end-to-end (E2E) pipeline execution before marking tasks complete.
- **Security Auditor:** Protect the 45000+ port range, enforce HMAC signatures on webhooks, and validate environment isolation (`.env`).
- **Django Architect & Evangelist:** While the tech stack is Flask+Alpine, architectural purity (lazy database initialization, decoupled models, strict MVC-like routing) must be treated with Django-level rigor.

**VIBE CODING RULES (Zero Exceptions):**
1. **NO BULLSHIT:** No placeholders, stubs, "TODOs", or fake APIs. Implementations must be real.
2. **CHECK FIRST, CODE SECOND:** Always read files and verify infrastructure state (via Docker logs, curl, etc.) before making edits.
3. **DOCUMENTATION = TRUTH:** The SRS (docs/avender_srs_master.md) is the absolute truth. Do not invent features outside the SRS.

---

## 2. Infrastructure & Deployment Rules

### 2.1 The 45000+ Port Authority Isolation
The ¡A VENDER! cluster runs completely isolated from standard dev ports to prevent collisions.
- **Port 45000:** SysAdmin Django Control Plane (Tenant lifecycle, billing, Vultr provisioning).
- **Port 45001:** Agent Zero Cognitive Engine (maps to internal port `80` run by Uvicorn/Supervisord).
- **Port 45002:** Whisper Server (Transcription Engine).

### 2.2 Production Docker-Compose Standards
All deployments MUST use `deployments/avender/docker-compose.yml` and adhere to:
- **Sequential Boot Sequence:** `sysadmin` → `whisper` → `agent_zero`.
- **Health Checks:** Every service must have a native health check (using `python3` or `curl`; avoid `wget --spider` due to redirect issues).
- **Memory Sovereignty:** Hard caps configured via `deploy.resources.limits.memory`. Total cluster budget is ~5GB.
- **Environment Isolation:** Secrets live ONLY in `deployments/avender/.env`. `OPENROUTER_API_KEY` is specifically EXCLUDED from docker-compose; it is managed securely inside the A0 UI settings.

### 2.3 WhatsApp Integration
WhatsApp messaging is handled entirely by Agent Zero's built-in `_whatsapp_integration` plugin:
- **Baileys Bridge:** Native Node.js bridge running on internal port 3100.
- **Message Polling:** `_10_wa_poll.py` extension polls the bridge for new messages.
- **Reply Routing:** `_55_wa_reply.py` extension auto-sends agent responses back via WhatsApp.
- **Audio Handling:** Audio attachments are downloaded and transcribed via Whisper.
- **Avender hooks into this pipeline** via system prompt extensions (`_40_avender_business_rules.py`) — NOT via a separate webhook handler.

---

## 3. Omni-Industry Data Architecture (JSONB/EAV)

### 3.1 The Generic Archetype Paradigm
The platform is agnostic. It serves Restaurants, Medical Clinics, Real Estate, Retail, etc.
- **NEVER hardcode industry-specific columns** (like `calories` or `doctor_name`) into SQLite schemas.
- **ALWAYS use the JSONB / EAV Pattern:** The `catalog_item` and `interaction_record` tables in `helpers/db.py` rely on a `metadata TEXT DEFAULT '{}'` column to store dynamic JSON payloads specific to the tenant's archetype.

### 3.2 Database Initialization Protocol
- **Lazy Initialization Only:** The `db.py` module uses a decorator (`@ensure_connection`) to lazily initialize the schema on the *first database call*.
- **NO Eager Loading:** Never run schema creation scripts purely upon module import, as it causes blocking side-effects during framework boot or plugin discovery.

---

## 4. The Cognitive Sales Pipeline

1. **Audio/Text Ingestion:** WhatsApp messages arrive via the Agent Zero `_whatsapp_integration` plugin's Baileys bridge polling loop.
2. **Security & Rate Limiting:** HMAC signature validated. Token-bucket rate limiter enforced to prevent spam loops.
3. **Transcription:** OGG files are downloaded and piped to the local Whisper server (Port 45002) synchronously.
4. **Agent Zero Context:** Messages are dispatched to an AgentContext. The avender system prompt extension (`_40_avender_business_rules.py`) injects tenant configuration (catalog, hours, delivery rules) into the agent's context.
5. **Tool Execution:** The agent interacts dynamically with `db.py` to check the catalog, or uses `handoff_to_human.py` to pause automation.
6. **Reply:** The framework's `_55_wa_reply.py` extension automatically sends the agent's response back via the Baileys bridge.
7. **Idempotency:** `save_interaction.py` guarantees events (like placing an order or booking an appointment) are deduplicated within a 30-second window using a SHA256 payload hash.

---

## 5. Development Workflow

- If touching **WhatsApp Integration**, use the existing `_whatsapp_integration` plugin. Never create duplicate webhook handlers.
- If touching **Infrastructure**, execute `docker compose down 2>&1 && docker compose up -d 2>&1` and use `docker compose ps` to verify the state.
- If touching **UI**, use Lit Web Component patterns as mandated by the global rules.
