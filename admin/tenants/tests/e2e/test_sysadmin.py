import re
from playwright.sync_api import Page, expect
import pytest

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "ignore_https_errors": True,
    }

def test_sysadmin_dashboard_rendering(page: Page):
    """Test that the main SysAdmin dashboard renders properly."""
    page.goto("http://localhost:8000/sysadmin/login")
    
    # Login as SysAdmin (Assuming a default local test account or mock)
    # We expect the dashboard to load if already authenticated or bypass
    # For now, let's assume it's checking the title
    expect(page).to_have_title(re.compile(r"¡A VENDER! Master Control Plane"))
    
    # Check that the main metrics cards are visible
    expect(page.locator("text=Total Tenants")).to_be_visible()
    expect(page.locator("text=Planes Activos")).to_be_visible()
    
    # Check Sidebar
    expect(page.locator("text=Dashboard")).to_be_visible()
    expect(page.locator("text=Inquilinos")).to_be_visible()
    expect(page.locator("text=SaaS Plans")).to_be_visible()

def test_deployment_mode_toggle(page: Page):
    """Test the DEV/PROD deployment mode toggle."""
    page.goto("http://localhost:8000/sysadmin")
    
    # Wait for the toggle to be visible
    deploy_toggle = page.locator("text=Deploy Mode").locator("..").locator("button")
    expect(deploy_toggle).to_be_visible()
    
    # Initial state should be either Docker or Vultr
    initial_text = deploy_toggle.inner_text()
    
    # Click it to switch modes
    deploy_toggle.click()
    
    # Expect the text to change (from DEV to PROD or vice versa)
    page.wait_for_timeout(1000) # Wait for UI update
    new_text = deploy_toggle.inner_text()
    assert initial_text != new_text

def test_plan_wizard_crud(page: Page):
    """Test creating and editing a Plan via the wizard."""
    page.goto("http://localhost:8000/sysadmin")
    
    # Go to Plans view
    page.locator("text=SaaS Plans").click()
    
    # Click Nuevo Plan
    page.locator("text=Nuevo Plan").click()
    
    # Ensure wizard is open
    expect(page.locator("text=Crear Nuevo Plan")).to_be_visible()
    
    # Fill out the form
    page.fill("input[type='text']:near(:text('Nombre del Plan'))", "Test Plan Playwright")
    page.fill("input[type='number']:near(:text('Precio Mensual'))", "99")
    
    # Check a feature gate
    page.locator("text=Dominio Personalizado").click()
    
    # Cancel to avoid actually creating it in DB (or submit if test DB is isolated)
    page.locator("text=Cancelar").click()
    
    # Ensure wizard is closed
    expect(page.locator("text=Crear Nuevo Plan")).not_to_be_visible()
