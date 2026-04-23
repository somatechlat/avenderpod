import pytest
from playwright.sync_api import Page, expect
import os

# To run this test, use: pytest tests/e2e/test_avender_onboarding.py -v

BASE_URL = os.getenv("PLAYWRIGHT_BASE_URL", "http://localhost:45001")

def test_avender_onboarding_full_flow(page: Page):
    """
    Test the entire Zero-Friction onboarding flow via the Web UI.
    Navigates through the 7 steps and verifies the final submission.
    """
    
    # 1. Login (if required by the environment)
    page.goto(f"{BASE_URL}/login")
    if page.locator("input[name='username']").is_visible():
        page.fill("input[name='username']", os.getenv("AUTH_LOGIN", "admin"))
        page.fill("input[name='password']", os.getenv("AUTH_PASSWORD", "admin"))
        page.click("button[type='submit']")
        page.wait_for_url("**/")

    # 2. Go to the Onboarding Wizard
    page.goto(f"{BASE_URL}/usr/plugins/avender/webui/onboarding.html")
    expect(page).to_have_title("¡A VENDER! - Onboarding")

    # -- Step 1: Datos de tu Negocio --
    expect(page.locator("h2").filter(has_text="Paso 1: Datos de tu Negocio")).to_be_visible()
    page.fill("input[placeholder='Ej: Restaurante El Buen Sabor']", "Restaurante E2E Test")
    page.select_option("select", "RUC")
    page.fill("input[placeholder='Ej: 1791234567001']", "1791234567001")
    page.check("input[type='checkbox']")  # accept terms
    page.click("button:has-text('Siguiente')")

    # -- Step 2: Operaciones y Delivery --
    expect(page.locator("h2").filter(has_text="Paso 2: Operaciones y Delivery")).to_be_visible()
    # Click to use current location (mocked or just click)
    page.click("button:has-text('🗺️ Capturar mi ubicación actual')")
    page.wait_for_timeout(1000) # Wait for Leaflet to catch up
    page.fill("textarea", "Av. Principal y Secundaria, E2E Test")
    page.click("button:has-text('Siguiente')")

    # -- Step 3: Industria y Catálogo --
    expect(page.locator("h2").filter(has_text="Paso 3: Industria y Catálogo")).to_be_visible()
    # Click the "Restaurante / Comidas" card
    page.click("div:has-text('🍔') >> text=Restaurante / Comidas")
    page.click("button:has-text('Siguiente')")

    # -- Step 4: Personalidad --
    expect(page.locator("h2").filter(has_text="Paso 4: Personalidad")).to_be_visible()
    page.fill("input[placeholder='Ej: Sofía, Carlos, Asistente Estrella']", "Vendedor E2E")
    page.select_option("select", "persuasive")
    page.check("input[type='checkbox']") # Hablar como Ecuatoriano
    page.click("button:has-text('Siguiente')")

    # -- Step 5: WhatsApp y Seguridad --
    expect(page.locator("h2").filter(has_text="Paso 5: WhatsApp y Seguridad")).to_be_visible()
    # Find the input that has a placeholder starting with +593
    page.fill("input[placeholder='+593 9...']", "+593997202547")
    # Fill the adminPassword field
    page.fill("input[type='password']", "SecureAdminPass123!")
    # Check "Restringir Acceso"
    # Find the checkbox near "Restringir Acceso"
    page.check("input[type='checkbox']")
    # Fill allowed numbers
    page.fill("textarea[placeholder='+593912345678, +593987654321']", "+593997202547, +593911111111")
    page.click("button:has-text('Siguiente')")

    # -- Step 6: Cierre (¡Casi terminamos!) --
    expect(page.locator("h2").filter(has_text="¡Casi terminamos!")).to_be_visible()
    page.click("button:has-text('¡Terminar y Activar!')")

    # -- Step 7: Éxito --
    # Wait for the success screen
    expect(page.locator("h2").filter(has_text="¡Configuración guardada exitosamente!")).to_be_visible(timeout=10000)
    expect(page.locator("text=Tu vendedor ha sido contratado")).to_be_visible()

    # Finish
    print("✅ E2E Playwright Test completed successfully! Whole flow verified.")
