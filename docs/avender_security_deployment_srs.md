# Avender Security Deployment SRS

Generated: 2026-05-09

## 1. Purpose And Scope

This document is the source of truth for Avender Pod deployment through the SysAdmin control plane. It covers pod registration, lifecycle actions, RBAC, rate-limit propagation, Vault isolation, impersonation, and UI constraints.

## 2. Mandatory Rules

- SysAdmin control-plane UI uses the existing Lit stack with Django/Ninja APIs.
- Avender Pod UI/code stays on its existing stack unless a targeted security fix is required.
- SysAdmin backend uses Django/Ninja and Django ORM only.
- SysAdmin user-facing strings must use `admin.common.messages.get_message()`.
- Secrets must not be stored in Docker env, Compose env, `.env`, browser storage, source, docs, or plaintext deployment files.
- Rate limits are non-secret and may be passed as container runtime config.
- Pod lifecycle actions must be RBAC-protected and audited.
- SysAdmin pod state must come from database lifecycle state, with provider health checks recorded separately.

## 3. Current Findings

- `admin/tenants/management/commands/register_dev_tenant.py` hardcoded a development tenant, container name, and port. Dev registration must verify the real Docker container exists before creating or refreshing a registry entry.
- `Tenant` stored deployment IDs directly, but that is not sufficient as a pod registry.
- Docker deployment previously merged all bootstrap values into container env, including tenant secrets.
- Vultr cloud-init previously wrote tenant secrets to plaintext files on the VM.
- `build_tenant_bootstrap_env()` mixed rate-limit config with secret values.
- Avender onboarding persisted sensitive browser values; sensitive fields must not be stored.
- `deployments/avender/docker-compose.yml` had a hardcoded `MASTER_CREATOR_PASSWORD` fallback; that has to be replaced by Vault/secret-file input and rotated.

## 4. Current Remediation Status

Implemented in this remediation pass:

- Added `PodDeployment` as the database-backed pod registry with lifecycle state, provider health, tenant Vault state, rate-limit snapshot, image, ports, URLs, and action metadata.
- Added RBAC-protected pod APIs for list, detail, refresh health, stop, suspend, reactivate, restart, delete, reconcile, and logs.
- Added SysAdmin Lit dashboard Pods view backed by real `PodDeployment` API data.
- Updated Docker and Vultr deployment paths to reject secret keys in container environment input and register successful deployments in `PodDeployment`.
- Docker deployments create a tenant-local Vault container, write only that tenant's secrets to it, create a scoped runtime token, and mount the token into the Avender container as a secret file.
- Split non-secret deployment config from tenant secret provisioning so rate limits remain container config and tenant secrets do not enter the same bootstrap object.
- Added plan validation for negative limits, invalid CPU, invalid memory, image names, and Vultr plan strings.
- Updated creator override verification so impersonation requires RBAC and the full live PIN, with pending challenge APIs masking the PIN.
- Removed hardcoded Compose secret fallback for `MASTER_CREATOR_PASSWORD` and replaced it with secret-file input.
- Removed sensitive Avender onboarding values from browser persistence.
- Updated dev tenant registration so it only registers an actual Docker container.
- Replaced SysAdmin remote Lit, Tailwind, and Google Font runtime dependencies with local static assets or system font fallback.

Still required before production cutover:

- Implement secure Vultr post-boot tenant Vault secret delivery. Current code refuses to put tenant secrets in Vultr cloud-init metadata.
- Rotate all previously exposed plaintext secrets from `deployments/avender/secrets/`, `deployments/avender/.env`, and `usr/.env`.
- Add provider-level Vault health checks for Vultr after secure tenant Vault delivery exists.

## 5. Target Architecture

SysAdmin owns tenants, plans, pod registry, lifecycle actions, RBAC, reconciliation, provisioning, audit events, and SysAdmin Vault.

Each Avender Pod stack owns:

- Avender runtime container
- tenant-local Vault container
- tenant-local network and volume state
- runtime secrets for only that tenant

SysAdmin Vault is required for provisioning and rotation. Existing Avender Pods must continue to run if SysAdmin Vault is unavailable. Tenant runtime secrets must be read from tenant-local Vault.

## 6. Pod Registry

The `PodDeployment` model is the database source for pod visibility. It records tenant, pod name, backend, provider IDs, container IDs, tenant Vault container ID, image, port/URLs, plan snapshot, rate-limit snapshot, lifecycle state, provider health state, tenant Vault state, last action, last actor, last health check, and last error.

Required lifecycle states:

- `provisioning`
- `active`
- `stopped`
- `restarting`
- `suspended`
- `deleting`
- `deleted`
- `failed`
- `degraded`
- `drifted`
- `unknown`

Provider health can mark a pod as missing or unhealthy, but it must not silently replace the database lifecycle state.

## 7. Lifecycle And RBAC

Required lifecycle actions:

- stop
- restart
- delete
- suspend
- reactivate
- refresh health
- reconcile
- view logs

Required pod permissions:

- `tenants.view_poddeployment`
- `tenants.deploy_poddeployment`
- `tenants.stop_poddeployment`
- `tenants.restart_poddeployment`
- `tenants.suspend_poddeployment`
- `tenants.reactivate_poddeployment`
- `tenants.delete_poddeployment`
- `tenants.reconcile_poddeployment`
- `tenants.view_pod_logs`
- `tenants.view_pod_health`

Each action must check RBAC before provider calls and write an `AuditEvent`.

## 8. Rate-Limit Propagation

`Plan` remains the source for rate limits. Deployment config may include:

- `A0_MAX_CONVERSATIONS_PER_MONTH`
- `A0_MAX_MESSAGES_PER_DAY`
- `A0_MAX_MESSAGES_PER_MINUTE`
- `A0_MAX_WHATSAPP_NUMBERS`
- `A0_MAX_CATALOG_ITEMS`
- `A0_MAX_TRANSCRIPTION_MINUTES_PER_MONTH`
- `A0_MAX_STORAGE_MB`
- `A0_MAX_USERS`
- `A0_MAX_AGENT_CONTEXTS`
- `A0_ALLOW_*`
- CPU and memory limits
- tenant ID, plan ID/name, image, assigned port
- tenant-local Vault address/path reference

Deployment config must never contain `SYSADMIN_API_KEY`, `SYSADMIN_TENANT_API_KEY`, `AVENDER_SETUP_TOKEN`, `MCP_SERVER_TOKEN`, Vault root/unseal tokens, or passwords.

## 9. Secret And Vault Flow

Provisioning flow:

1. SysAdmin creates tenant and effective plan snapshot.
2. SysAdmin generates tenant secret bundle.
3. SysAdmin stores provisioning reference/copy in SysAdmin Vault.
4. Deployment creates Avender container and tenant-local Vault container.
5. SysAdmin writes only that tenant's runtime secrets into tenant-local Vault.
6. Avender starts with tenant-local Vault reference only.
7. Avender reads runtime secrets from tenant-local Vault.

Existing plaintext secrets under `deployments/avender/secrets/`, `deployments/avender/.env`, and `usr/.env` must be treated as exposed and rotated.

## 10. Creator Override / Impersonation

Impersonation requires the full live PIN from the user-side Avender session.

Required flow:

1. User initiates Creator Override in Avender Pod.
2. Avender Pod calls SysAdmin `init-challenge` with tenant-scoped auth.
3. SysAdmin stores only a PIN hash and expiry.
4. Raw PIN is displayed only to the requesting user/session.
5. SysAdmin pending challenge APIs show tenant/session metadata and masked PIN only.
6. SysAdmin operator enters master credential and the full PIN.
7. `verify-challenge` validates RBAC, tenant scope, credential, full PIN hash, expiry, and single-use status.
8. Success clears the PIN and writes audit events for verification and impersonation start.

Required permissions:

- `tenants.initiate_creator_override`
- `tenants.verify_creator_override`
- `tenants.impersonate_tenant`
- `tenants.view_creator_challenge`

## 11. UI Requirements

SysAdmin Lit + Django/Ninja UI must include a Pods view backed by `PodDeployment` APIs. It must show tenant, plan, backend, lifecycle state, provider health, tenant Vault state, image, URL/port, rate limits, last health check, and last error.

Avender Pod UI stays on its current stack. Browser storage must not persist passwords, setup tokens, API keys, auth tokens, or Creator Override PINs.

## 12. Acceptance Criteria

- SysAdmin displays real pods from `PodDeployment`, not fake rows.
- Stop, restart, delete, suspend, and reactivate are RBAC-protected and audited.
- Reconciliation marks drift and missing provider resources.
- Docker inspect shows rate limits but no secrets.
- Existing pods run without SysAdmin Vault.
- Avender fails closed if tenant-local Vault is unavailable.
- Impersonation cannot start without the full live PIN.
- Pending challenge lists never expose raw PINs.
- Avender Pod stack is not migrated as part of SysAdmin work; only sensitive browser persistence is remediated.
