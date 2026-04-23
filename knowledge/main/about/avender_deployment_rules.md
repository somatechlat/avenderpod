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
- **Port 45001:** Agent Zero Cognitive Engine (maps to internal port `80` run by Uvicorn/Supervisord).
- **Port 45002:** Whisper Server (Transcription Engine).
- **Port 45003:** Chatwoot Web UI (Tier 1 Systems Control).

### 2.2 Production Docker-Compose Standards
All deployments MUST use `deployments/avender/docker-compose.yml` and adhere to:
- **Sequential Boot Sequence:** `postgres` → `redis` → `chatwoot_migrate` → `chatwoot_web` / `chatwoot_worker` → `whisper` → `agent_zero`.
- **Health Checks:** Every service must have a native health check (using `ruby`, `python3`, or native CLI tools; avoid `wget --spider` due to redirect issues).
- **Memory Sovereignty:** Hard caps configured via `deploy.resources.limits.memory`. Total cluster budget is ~6.5GB.
- **Environment Isolation:** Secrets live ONLY in `deployments/avender/.env`. `OPENROUTER_API_KEY` is specifically EXCLUDED from docker-compose; it is managed securely inside the A0 UI settings.

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

1. **Audio/Text Ingestion:** WhatsApp webhook hits `chatwoot.py`.
2. **Security & Rate Limiting:** HMAC signature validated. Token-bucket rate limiter enforced to prevent spam loops.
3. **Transcription:** OGG files are downloaded and piped to the local Whisper server (Port 45002) synchronously.
4. **Agent Zero Hook:** Text is pushed to the `_55_chatwoot_reply.py` extension, which injects the `chatwoot_account_id` and tenant configuration into the agent context.
5. **Tool Execution:** The agent interacts dynamically with `db.py` to check the catalog, or uses `handoff_to_human.py` to pause automation.
6. **Idempotency:** `save_interaction.py` guarantees events (like placing an order or booking an appointment) are deduplicated within a 30-second window using a SHA256 payload hash.

---

## 5. Development Workflow

- If touching **Chatwoot Integration**, verify the `chatwoot_account_id` mapping. Never hardcode `accounts/1`.
- If touching **Infrastructure**, execute `docker compose down 2>&1 && docker compose up -d 2>&1` and use `docker compose ps` to verify the state.
- If touching **UI**, use the existing Alpine.js patterns without migrating back to legacy frameworks, but remember new architectural UI additions should follow Lit Web Component patterns as mandated by the global rules.
