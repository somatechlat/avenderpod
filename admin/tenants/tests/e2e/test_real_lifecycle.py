"""
E2E Test: Full SysAdmin Lifecycle — Plan + Tenant + Docker Deployment

REAL E2E flow. No mocks. No stubs.
Tests the complete lifecycle:
  1. Login with real superuser credentials
  2. Create a Plan with rate limits via API
  3. Set deployment mode to Docker
  4. Create a Tenant via API (triggers real Docker provisioning)
  5. Verify tenant appears in the UI as ACTIVE + DOCKER
  6. Verify the deployed container has the correct rate-limit env vars
  7. Clean up: delete the container and tenant

Requires:
  TEST_PASSWORD env var — the Django superuser password.
  SYSADMIN_URL env var — base URL (default: http://localhost:45000).

Run:
  TEST_PASSWORD=<pwd> pytest admin/tenants/tests/e2e/test_real_lifecycle.py -v --headed
"""

import os
import time

import docker
from docker.errors import NotFound

try:
    import pytest
    from playwright.sync_api import Page, expect
    _HAS_E2E_DEPS = True
except ImportError:
    pytest = None
    Page = object
    expect = None
    _HAS_E2E_DEPS = False

BASE_URL = os.environ.get("SYSADMIN_URL", "http://localhost:45000")


def _skip_if_no_deps():
    if not _HAS_E2E_DEPS:
        raise RuntimeError("E2E dependencies missing (pytest, playwright). Run: pip install pytest playwright")


if _HAS_E2E_DEPS:
    @pytest.fixture(scope="session")
    def browser_context_args(browser_context_args):
        return {
            **browser_context_args,
            "ignore_https_errors": True,
        }


def test_real_lifecycle(page: Page):
    """
    REAL E2E Flow: No mocks.
    Logs in with real superuser credentials, creates a real Plan via API,
    creates a real Tenant via API, and waits for real Docker provisioning
    via UI observation.  Then verifies rate-limit env vars on the
    deployed container and cleans up.
    """
    _skip_if_no_deps()

    ts = int(time.time())
    tenant_id = None
    plan_id = None
    container = None
    client = docker.from_env()
    headers = {}

    try:
        # ──────────────────────────────────────────────────────────────────
        # 1. AUTHENTICATION FLOW
        # ──────────────────────────────────────────────────────────────────
        page.goto(f"{BASE_URL}/login/")

        username = os.environ.get("TEST_USERNAME", "admin")
        password = os.environ.get("TEST_PASSWORD")
        assert password, "TEST_PASSWORD environment variable is required for real E2E."

        page.fill("#id_username", username)
        page.fill("#id_password", password)
        page.locator("text=Iniciar Sesión Segura").click()

        # Wait for Lit web component to hydrate
        page.wait_for_selector("saas-control-plane", state="attached", timeout=15000)
        page.evaluate("customElements.whenDefined('saas-control-plane')")
        page.wait_for_timeout(2000)

        # Extract CSRF token for API calls
        csrf_token = page.locator('meta[name="csrf-token"]').get_attribute("content")
        assert csrf_token, "CSRF token not found in DOM"

        headers = {"X-CSRFToken": csrf_token, "Referer": f"{BASE_URL}/saas/"}

        # ──────────────────────────────────────────────────────────────────
        # 2. PLAN CREATION (via API) — with explicit rate limits
        # ──────────────────────────────────────────────────────────────────
        plan_name = f"E2E-Plan-{ts}"
        plan_data = {
            "name": plan_name,
            "price_monthly": 49.99,
            "max_conversations": 100,
            "max_numbers": 1,
            "max_messages_per_day": 500,
            "max_messages_per_minute": 30,
            "max_catalog_items": 100,
            "max_transcription_minutes": 60,
            "max_storage_mb": 512,
            "max_users": 2,
            "max_agent_contexts": 1,
            "vultr_plan": "vc2-1c-1gb",
            "a0_image": "avenderpod:latest",
            "a0_memory_limit": "64m",
            "a0_cpu_limit": "0.5",
            "a0_memory_reservation": "32m",
            "a0_cpu_reservation": "0.25",
            "allow_catalog_upload": True,
            "allow_voice_messages": True,
            "allow_human_handoff": False,
            "allow_creator_override": False,
            "is_active": True,
        }

        response = page.request.post(
            f"{BASE_URL}/api/saas/plans", data=plan_data, headers=headers
        )
        assert response.ok, (
            f"Plan creation failed: {response.status} {response.status_text}"
        )
        plan_json = response.json()
        plan_id = plan_json.get("id")

        # ──────────────────────────────────────────────────────────────────
        # 3. SET DEPLOYMENT MODE TO DOCKER
        # ──────────────────────────────────────────────────────────────────
        mode_resp = page.request.post(
            f"{BASE_URL}/api/saas/system/deployment-mode",
            data={"mode": "docker"},
            headers=headers,
        )
        assert mode_resp.ok, (
            f"Set deployment mode failed: {mode_resp.status}"
        )

        # ──────────────────────────────────────────────────────────────────
        # 4. TENANT CREATION (via API) — triggers Docker deployment
        # ──────────────────────────────────────────────────────────────────
        tenant_name = f"e2e-tenant-{ts}"
        tenant_data = {
            "business_name": tenant_name,
            "owner_full_name": "E2E Tester",
            "owner_email": f"e2e-{ts}@somatech.ec",
            "owner_phone_e164": "+593900000000",
            "plan_name": plan_name,
        }

        tenant_resp = page.request.post(
            f"{BASE_URL}/api/saas/tenants", data=tenant_data, headers=headers
        )
        if not tenant_resp.ok:
            try:
                err = tenant_resp.json()
                msg = err.get("detail", err.get("message", tenant_resp.text()))
            except Exception:
                msg = tenant_resp.text()
            pytest.fail(
                f"Tenant creation failed: {tenant_resp.status} "
                f"{tenant_resp.status_text} — {msg}"
            )

        tenant_json = tenant_resp.json()
        tenant_id = tenant_json.get("id")

        # ──────────────────────────────────────────────────────────────────
        # 5. UI VERIFICATION — tenant appears as ACTIVE + DOCKER
        # ──────────────────────────────────────────────────────────────────
        page.goto(f"{BASE_URL}/")
        page.wait_for_selector("saas-control-plane", state="attached", timeout=15000)

        # Navigate to tenants tab
        page.get_by_text("Inquilinos (Tenants)").click()

        # Wait for the tenant row to appear (Docker deploy may take a few seconds)
        expect(page.get_by_text(tenant_name)).to_be_visible(timeout=60000)

        tenant_row = page.locator("tr", has_text=tenant_name)
        expect(tenant_row.locator("text=ACTIVE")).to_be_visible(timeout=60000)
        expect(tenant_row.locator("text=DOCKER")).to_be_visible()

        # ──────────────────────────────────────────────────────────────────
        # 6. CONTAINER VERIFICATION — rate limits injected correctly
        # ──────────────────────────────────────────────────────────────────

        # Find the container by the avender-pod naming convention
        for c in client.containers.list(all=True):
            if tenant_id and tenant_id[:12] in c.name:
                container = c
                break

        assert container is not None, (
            f"Docker container for tenant {tenant_id} not found"
        )

        inspect = container.attrs
        env_list = inspect["Config"]["Env"]
        env_dict = {
            e.split("=", 1)[0]: e.split("=", 1)[1]
            for e in env_list
            if "=" in e
        }

        # Verify rate limits match the plan
        assert env_dict.get("A0_MAX_MESSAGES_PER_DAY") == "500", (
            f"Expected 500, got {env_dict.get('A0_MAX_MESSAGES_PER_DAY')}"
        )
        assert env_dict.get("A0_MAX_CONVERSATIONS_PER_MONTH") == "100", (
            f"Expected 100, got {env_dict.get('A0_MAX_CONVERSATIONS_PER_MONTH')}"
        )
        assert env_dict.get("TENANT_ID") == str(tenant_id), (
            f"Expected {tenant_id}, got {env_dict.get('TENANT_ID')}"
        )

        # Verify resource limits
        mem = inspect["HostConfig"]["Memory"]
        assert mem == 64 * 1024 * 1024, f"Expected 64MB, got {mem}"

        cpu = inspect["HostConfig"]["NanoCpus"]
        assert cpu == 500_000_000, f"Expected 0.5 CPU, got {cpu}"

        # Verify image is avenderpod:latest
        img = inspect["Config"]["Image"]
        assert "avenderpod" in img, f"Expected avenderpod image, got {img}"

    finally:
        # ──────────────────────────────────────────────────────────────────
        # 7. CLEANUP — delete container and tenant regardless of test result
        # ──────────────────────────────────────────────────────────────────
        if container is not None:
            try:
                container.stop(timeout=3)
                container.remove(force=True)
            except Exception:
                pass  # Best effort

        if tenant_id is not None:
            try:
                delete_resp = page.request.delete(
                    f"{BASE_URL}/api/saas/tenants/{tenant_id}",
                    headers=headers,
                )
                # Accept 200, 204, or 404 (if already deleted)
                assert delete_resp.status in (200, 204, 404), (
                    f"Unexpected delete response: {delete_resp.status}"
                )
            except Exception:
                pass  # Best effort

        if plan_id is not None:
            try:
                page.request.delete(
                    f"{BASE_URL}/api/saas/plans/{plan_id}",
                    headers=headers,
                )
            except Exception:
                pass  # Best effort
