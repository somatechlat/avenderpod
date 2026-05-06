import os
import time
import pytest
from playwright.sync_api import Page, expect

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
    creates a real Tenant via API, and waits for real Docker provisioning via UI observation.
    """
    
    # 1. AUTHENTICATION FLOW
    page.goto("http://localhost:8080/login/")
    
    username = os.environ.get("TEST_USERNAME", "admin")
    password = os.environ.get("TEST_PASSWORD")
    assert password, "TEST_PASSWORD environment variable is required for real E2E."
    
    page.fill("#id_username", username)
    page.fill("#id_password", password)
    page.locator("text=Iniciar Sesión Segura").click()
    
    # Expect redirect to dashboard and wait for the web component to load
    page.wait_for_selector("saas-control-plane", state="attached", timeout=15000)
    page.evaluate("customElements.whenDefined('saas-control-plane')")
    page.wait_for_timeout(2000)
    
    # Extract CSRF token
    csrf_token = page.locator('meta[name="csrf-token"]').get_attribute("content")
    assert csrf_token, "CSRF token not found in DOM"
    
    # 2. PLAN CREATION FLOW (via API)
    plan_name = f"Playwright Plan {int(time.time())}"
    plan_data = {
        "name": plan_name,
        "price_monthly": 49.99,
        "max_conversations": 100,
        "max_numbers": 1,
        "max_messages_per_day": 500,
        "max_messages_per_minute": 30,
        "max_catalog_items": 100,
        "max_transcription_minutes": 60,
        "vultr_plan": "vc2-1c-1gb",
        "a0_image": "avender-agent_zero:latest",
        "a0_memory_limit": "1g",
        "a0_cpu_limit": "1.0",
        "a0_memory_reservation": "512m",
        "a0_cpu_reservation": "0.5",
        "allow_catalog_upload": True,
        "allow_voice_messages": True,
        "allow_human_handoff": False,
        "allow_creator_override": False,
        "is_active": True
    }
    
    response = page.request.post(
        "http://localhost:8080/api/saas/plans",
        data=plan_data,
        headers={"X-CSRFToken": csrf_token, "Referer": "http://localhost:8080/saas/"}
    )
    assert response.ok, f"Failed to create plan: {response.status} {response.status_text}"
    
    # 3. SET DEPLOYMENT MODE TO DOCKER
    # We must explicitly set it to Docker to bypass Vultr API calls in the E2E test
    mode_response = page.request.post(
        "http://localhost:8080/api/saas/system/deployment-mode",
        data={"mode": "docker"},
        headers={"X-CSRFToken": csrf_token, "Referer": "http://localhost:8080/saas/"}
    )
    assert mode_response.ok, f"Failed to set deployment mode: {mode_response.status}"

    # 4. TENANT CREATION FLOW (via API)
    tenant_name = f"plw-tenant-{int(time.time())}"
    tenant_data = {
        "business_name": tenant_name,
        "owner_full_name": "Playwright Tester",
        "owner_email": f"tester-{int(time.time())}@somatech.ec",
        "owner_phone_e164": "+593900000000",
        "plan_name": plan_name
    }
    
    tenant_response = page.request.post(
        "http://localhost:8080/api/saas/tenants",
        data=tenant_data,
        headers={"X-CSRFToken": csrf_token, "Referer": "http://localhost:8080/saas/"}
    )
    if not tenant_response.ok:
        try:
            err_json = tenant_response.json()
            err_msg = err_json.get("detail", err_json.get("message", tenant_response.text()))
        except Exception:
            err_msg = tenant_response.text()
        assert False, f"Failed to create tenant: {tenant_response.status} {tenant_response.status_text} - {err_msg}"
    
    # 4. ORCHESTRATION VERIFICATION (via UI)
    # The tenant should now be spinning up in Docker. Wait for it to become 'running'.
    # Refresh to see the new tenant in the UI
    page.goto("http://localhost:8080/")
    page.wait_for_selector("saas-control-plane", state="attached", timeout=15000)
    
    # Switch to the Tenants view to render the tenant list
    page.get_by_text("Inquilinos (Tenants)").click()
    
    # We use a longer timeout because docker run takes a few seconds
    expect(page.get_by_text(tenant_name)).to_be_visible(timeout=60000)
    
    tenant_row = page.locator("tr", has_text=tenant_name)
    expect(tenant_row.locator("text=ACTIVE")).to_be_visible(timeout=60000)
    expect(tenant_row.locator("text=DOCKER")).to_be_visible()
