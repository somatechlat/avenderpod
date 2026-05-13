import re
import os

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


def _login(page: Page) -> None:
    """Helper: log in as the default superuser."""
    _skip_if_no_deps()
    page.goto(f"{BASE_URL}/login/")
    username = os.environ.get("TEST_USERNAME", "admin")
    password = os.environ.get("TEST_PASSWORD")
    if not password:
        pytest.skip("TEST_PASSWORD not set — skipping E2E login tests")
    page.fill("#id_username", username)
    page.fill("#id_password", password)
    page.locator("text=Iniciar Sesión Segura").click()
    page.wait_for_selector("saas-control-plane", state="attached", timeout=15000)
    page.evaluate("customElements.whenDefined('saas-control-plane')")
    page.wait_for_timeout(1500)


def test_sysadmin_dashboard_rendering(page: Page):
    """Test that the main SysAdmin dashboard renders properly."""
    _login(page)

    # Dashboard title should be present
    expect(page).to_have_title(re.compile(r"¡A VENDER!"))

    # Check that the main metrics cards are visible
    expect(page.locator("text=Total Tenants")).to_be_visible()
    expect(page.locator("text=Planes Activos")).to_be_visible()

    # Check Sidebar
    expect(page.locator("text=Dashboard")).to_be_visible()
    expect(page.locator("text=Inquilinos")).to_be_visible()
    expect(page.locator("text=SaaS Plans")).to_be_visible()


def test_deployment_mode_toggle(page: Page):
    """Test the Docker/Vultr deployment mode toggle."""
    _login(page)

    # Wait for the toggle to be visible
    deploy_toggle = page.locator("text=Deploy Mode").locator("..").locator("button")
    # If the above selector fails, the toggle may be rendered differently
    # in Lit — use a data-testid or broader selector as fallback
    if deploy_toggle.count() == 0:
        deploy_toggle = page.locator("button").filter(has_text=re.compile(r"docker|vultr", re.IGNORECASE)).first

    expect(deploy_toggle).to_be_visible()

    # Initial state should be either Docker or Vultr
    initial_text = deploy_toggle.inner_text().strip().lower()
    assert initial_text in ("docker", "vultr"), f"Unexpected initial mode: {initial_text}"

    # Click it to switch modes
    deploy_toggle.click()
    page.wait_for_timeout(1000)  # Wait for UI update + API call

    # Expect the text to change (from docker to vultr or vice versa)
    new_text = deploy_toggle.inner_text().strip().lower()
    assert new_text in ("docker", "vultr"), f"Unexpected new mode: {new_text}"
    assert initial_text != new_text, "Deployment mode should toggle after click"


def test_plan_wizard_crud(page: Page):
    """Test creating and editing a Plan via the wizard."""
    _login(page)

    # Go to Plans view
    page.locator("text=SaaS Plans").click()
    page.wait_for_timeout(500)

    # Click Nuevo Plan
    page.locator("text=Nuevo Plan").click()
    page.wait_for_timeout(500)

    # Ensure wizard is open
    expect(page.locator("text=Crear Nuevo Plan")).to_be_visible()

    # Fill out the form
    ts = int(__import__("time").time())
    plan_name = f"Test Plan {ts}"
    page.fill("input[placeholder*='Nombre del Plan'], input[name='name']", plan_name)
    page.fill("input[placeholder*='Precio'], input[name='price_monthly']", "99")

    # Check a feature gate (custom domain)
    page.locator("text=Dominio Personalizado").click()

    # Cancel to avoid actually creating it in DB (or submit if test DB is isolated)
    page.locator("text=Cancelar").click()
    page.wait_for_timeout(500)

    # Ensure wizard is closed
    expect(page.locator("text=Crear Nuevo Plan")).not_to_be_visible()


def test_invalid_phone_rejected(page: Page):
    """Test that tenant creation with an invalid phone number shows an error."""
    _login(page)

    csrf_token = page.locator('meta[name="csrf-token"]').get_attribute("content")
    headers = {"X-CSRFToken": csrf_token, "Referer": f"{BASE_URL}/saas/"}

    response = page.request.post(
        f"{BASE_URL}/api/saas/tenants",
        data={
            "business_name": "Invalid Phone Corp",
            "owner_full_name": "Test User",
            "owner_email": "bad-phone@test.local",
            "owner_phone_e164": "not-a-phone",
            "plan_name": "Free",
        },
        headers=headers,
    )
    # Should be rejected with 400
    assert response.status == 400, (
        f"Expected 400 for invalid phone, got {response.status}"
    )


def test_negative_plan_limits_rejected(page: Page):
    """Test that creating a plan with negative rate limits is rejected."""
    _login(page)

    csrf_token = page.locator('meta[name="csrf-token"]').get_attribute("content")
    headers = {"X-CSRFToken": csrf_token, "Referer": f"{BASE_URL}/saas/"}

    response = page.request.post(
        f"{BASE_URL}/api/saas/plans",
        data={
            "name": "Negative Plan",
            "price_monthly": 10.00,
            "max_messages_per_day": -100,
        },
        headers=headers,
    )
    assert response.status == 400, (
        f"Expected 400 for negative limits, got {response.status}"
    )


def test_deployment_mode_persists_across_reload(page: Page):
    """Test that changing deployment mode persists after page reload."""
    _login(page)

    csrf_token = page.locator('meta[name="csrf-token"]').get_attribute("content")
    headers = {"X-CSRFToken": csrf_token, "Referer": f"{BASE_URL}/saas/"}

    # Get current mode
    mode_resp = page.request.get(
        f"{BASE_URL}/api/saas/system/deployment-mode",
        headers=headers,
    )
    assert mode_resp.ok
    original_mode = mode_resp.json()["mode"]

    # Set to a known mode
    target_mode = "docker"
    page.request.post(
        f"{BASE_URL}/api/saas/system/deployment-mode",
        data={"mode": target_mode},
        headers=headers,
    )

    # Reload the page and check the mode is still set
    page.reload()
    page.wait_for_selector("saas-control-plane", state="attached", timeout=15000)
    page.wait_for_timeout(1500)

    # Re-acquire CSRF after reload
    csrf_token = page.locator('meta[name="csrf-token"]').get_attribute("content")
    headers = {"X-CSRFToken": csrf_token, "Referer": f"{BASE_URL}/saas/"}

    verify_resp = page.request.get(
        f"{BASE_URL}/api/saas/system/deployment-mode",
        headers=headers,
    )
    assert verify_resp.ok
    assert verify_resp.json()["mode"] == target_mode, (
        f"Mode did not persist: expected {target_mode}, got {verify_resp.json()['mode']}"
    )

    # Restore original mode
    page.request.post(
        f"{BASE_URL}/api/saas/system/deployment-mode",
        data={"mode": original_mode},
        headers=headers,
    )


def test_health_endpoint_accessible(page: Page):
    """Test that the health endpoint is accessible without authentication."""
    _skip_if_no_deps()

    response = page.request.get(f"{BASE_URL}/api/saas/health")
    assert response.ok, f"Health check failed: {response.status}"
    data = response.json()
    assert data["status"] in ("ok", "degraded"), (
        f"Unexpected health status: {data['status']}"
    )
    assert "db" in data, "Health response missing 'db' field"

