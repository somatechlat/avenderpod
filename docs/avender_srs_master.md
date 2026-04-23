# ISO/IEC 29148:2018 Software Requirements Specification (SRS)
## ¡A VENDER! — Omni-Industry WhatsApp Sales Assistant
**Version:** 4.0 (Master Development File)
**Date:** 2026-04-23
**Status:** In Development / Production Deployment Phase

---

## 1. Introduction

### 1.1 Purpose
This document defines the Software Requirements Specification (SRS) for **¡A VENDER!**, an omni-industry autonomous sales assistant over WhatsApp. The system integrates Agent Zero (with its native WhatsApp Baileys bridge) and Whisper to provide 24/7 automated customer service, dynamic ordering, and appointment scheduling tailored to diverse industry archetypes.

### 1.2 Scope
¡A VENDER! is a SaaS platform allowing business owners across multiple verticals (Restaurants, Tourism, Clinics, Real Estate, Education, Retail, Gyms, Services) to configure a digital sales agent via a unified onboarding wizard. The assistant intelligently handles voice notes, processes locations, answers FAQs, schedules appointments, and closes sales autonomously without rigid menus.

---

## 2. Overall Description

### 2.1 Product Perspective
The system operates as a **Tiered Pod Architecture**:
* **Tier 0 (Control Plane):** Django + Ninja SysAdmin portal for tenant lifecycle management, Vultr provisioning, and platform health monitoring.
* **Tier 1.5 (Transcription):** Centralized `faster-whisper-server` (CPU-optimized) for processing audio notes.
* **Tier 2 (Cognitive Engine):** Agent Zero runtime orchestrating LLM logic (via OpenRouter/Nemotron), the custom `avender` plugin, and the native `_whatsapp_integration` plugin for Baileys-based WhatsApp connectivity.

### 2.2 User Characteristics
* **System Admin:** Uses the Django Control Plane (Port 45000) to manage tenants, monitor platform health, suspend/reactivate accounts, and oversee billing.
* **Tenant (Business Owner):** Uses a streamlined Onboarding Wizard to set up the business archetype, policies, pricing, and upload catalogs. No coding required. Accesses a Tenant Admin Dashboard (Lit Web Component) to monitor sales, edit catalog, and manage conversations.
* **End Customer:** Interacts purely via WhatsApp using natural language (text, voice, locations).

---

## 3. Specific Requirements

### 3.1 Onboarding & Setup (Wizard)
* **REQ-3.1.1 — Legal & Identity Capture:** Must capture RUC/Cédula, Razón Social, and Trade Name.
* **REQ-3.1.2 — Operations & Logistics:** Must capture headquarters, operating hours, delivery rules, and payment methods (Transfer, Cash, Payment Link).
* **REQ-3.1.3 — Omni-Industry Archetypes:** The onboarding wizard must support generic data scaffolding for the following archetypes:
  * **Retail & Food:** Carts, product catalogs, shipping costs.
  * **Medical & Services:** Appointments, doctor availability, clinical services.
  * **Real Estate & Vehicles:** Lead qualification, tour scheduling.
  * **Subscriptions & Education:** Memberships, recurring payments, class schedules.
* **REQ-3.1.4 — Personality Engine:** Assistant name, tone (friendly, formal, persuasive), slang usage toggle, and emoji density.
* **REQ-3.1.5 — Footer & Legal Compliance:** Persistent legal footer containing LOPDP links, Terms of Service, Cookies, and developer credits (Somatech / Yachaq).
* **REQ-3.1.6 — Fallback Catalog Presets:** The system automatically hydrates a default catalog containing 10 pre-defined items based on the archetype if no valid file is uploaded.
* **REQ-3.1.7 — AI Onboarding Copilot:** A live, floating AI chatbot powered by a 120B model must be accessible during enrollment to provide frictionless support ("What should I put in my delivery rules?").

### 3.2 Dynamic Omni-Industry Data Model (JSONB/EAV)
* **REQ-3.2.1 — Schema Purity:** The catalog and interaction databases MUST use a generic schema leveraging JSONB (SQLite JSON `metadata` column) to support varying properties per industry without DDL changes.
  * *Retail metadata:* `{ "price": 10.0, "stock": 50, "variants": ["S", "M", "L"] }`
  * *Medical metadata:* `{ "specialty": "Pediatría", "duration_mins": 30 }`
  * *Real Estate metadata:* `{ "bedrooms": 3, "area_m2": 120, "zone": "Norte" }`
* **REQ-3.2.2 — Interaction Recording:** A universal `interaction_record` table must capture diverse conversion events (sales, bookings, leads) dynamically.

### 3.3 Cognitive Loop & WhatsApp Integration
* **REQ-3.3.1 — Native WhatsApp Bridge:** All WhatsApp messaging is handled by Agent Zero's built-in `_whatsapp_integration` plugin using the Baileys bridge (port 3100 internal). No external messaging gateway is used.
* **REQ-3.3.2 — Whisper Bridge:** OGG audio files received via WhatsApp must be intercepted, downloaded, and sent to the Whisper API. The resulting text must be injected into the LLM context *before* cognitive processing.
* **REQ-3.3.3 — Rate Limiting:** Token-bucket rate limiting must protect the Agent against WhatsApp spam loops or denial of wallet attacks.
* **REQ-3.3.4 — Human Handoff:** Must support graceful escalation to human operators, silencing the bot until the human explicitly re-enables it.

### 3.4 Tool Execution Environment
* **REQ-3.4.1 — Sandbox Isolation:** The Agent must be restricted to Avender-specific tools. OS-level tools (terminal, file writes outside the tenant workspace) must be disabled via an extension interceptor.
* **REQ-3.4.2 — Context Injection:** The tool context must dynamically read the tenant's configuration (`archetype`, business rules) to interact with the correct database partition.

---

## 4. Current Development Status & Matrix

### 4.1 Production Cluster Readiness (COMPLETED)
* ✅ **Hardened Docker Stack:** 3 services (SysAdmin Django, Whisper, Agent Zero) isolated on ports 45000-45002.
* ✅ **Sequential Startup:** Health check dependencies ensure reliable boot sequence.
* ✅ **Memory Sovereignty:** Enforced RAM limits (~5GB total) via Docker `deploy.resources`.
* ✅ **Database Initialization:** `helpers/db.py` transitioned to lazy-loading to prevent schema instantiation bugs during module import.
* ✅ **Rate Limiting:** Token-bucket rate limiter implemented per WhatsApp sender.
* ✅ **Native WhatsApp Integration:** Uses Agent Zero's built-in `_whatsapp_integration` plugin with Baileys bridge.
* ✅ **SysAdmin Control Plane:** Django + Ninja portal at port 45000 with Django auth, tenant CRUD, suspend/reactivate, and Vultr API integration.
* ✅ **Tenant Admin Dashboard:** Lit Web Component dashboard with login gate, conversation inbox, catalog management, and KPI display.

### 4.2 Outstanding Development (PENDING)
* ❌ **Archetype-Specific Tool Injection:** Currently, all tools load simultaneously. Need dynamic tool filtering based on the `archetype` selected in the wizard.
* ✅ **Catalog Ingestion (File Upload):** (COMPLETED) The backend dynamically parses PDF, Excel, and Text files. It also uses Vision AI to parse photos of physical menus (.png, .jpg).
* ✅ **AI Onboarding Copilot:** (COMPLETED) Live assistant integrated directly into `onboarding.html`.
* ❌ **Payment Gateway:** Integrate SubscriptionPlan model with live payment gateway (Payphone/Stripe) for automated tenant provisioning.
* ❌ **Odoo Live Connector (Premium):** Dynamic synchronization tool for querying live Odoo 18 instances instead of the internal SQLite store.

---

## 5. Security & LOPDP Compliance
* **HMAC Validation:** Webhook signatures validated against `WEBHOOK_SECRET` to prevent spoofing.
* **Data Minimization:** LLM prompts tuned to extract only necessary information (name, phone, order details).
* **Admin Backdoor Timeout:** WhatsApp-based owner mode auto-expires after 10 minutes of inactivity.
* **ISO Compliance Note:** The architecture provides strict tenant separation via isolated JSON stores or schemas, aligning with Ecuadorian LOPDP requirements.
* **REQ-5.1.1 — File Ingestion Security:** All uploaded catalogs MUST be validated against a strict whitelist of extensions (`.png`, `.jpg`, `.jpeg`, `.pdf`, `.xls`, `.xlsx`, `.doc`, `.docx`, `.txt`, `.csv`). ZIP archives and executables are strictly prohibited to prevent code injection. File size is hard-capped at 100MB.
* **REQ-5.1.2 — WhatsApp Access Control:** The system allows tenants to capture their designated WhatsApp number during onboarding. It also provides a "Restrict Access" security feature, allowing the tenant to supply a comma-separated list of up to 100 authorized phone numbers. If enabled, the Agent MUST ignore all messages from unlisted numbers.
* **REQ-5.1.3 — Age Verification (18+):** For sensitive industries such as Liquor ("Licorería") and Cannabis/CBD ("Cannabis / CBD"), the system MUST enforce strict age verification in accordance with Ecuadorian regulations.
* **REQ-5.1.4 — SysAdmin Authentication:** The Django Control Plane requires Django superuser authentication. No anonymous access to tenant management.
* **REQ-5.1.5 — Tenant Admin Authentication:** The Tenant Admin dashboard requires password authentication via the `auth_api.py` session system.
* **REQ-5.1.6 — Secret Management:** No secrets in environment variables or source code. Django SECRET_KEY generated at runtime. Vultr API keys sourced from environment (Vault-ready pattern).

---
**End of Specification.**
