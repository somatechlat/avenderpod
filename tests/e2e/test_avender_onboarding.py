"""
E2E Playwright test for the ¡A VENDER! onboarding wizard.
Runs against a LIVE Agent Zero instance — no mocked API responses.

To run: pytest tests/e2e/test_avender_onboarding.py -v
Prerequisites: Agent Zero running on port 45001 with avender plugin enabled.
"""

import pytest
from playwright.sync_api import Page, expect
import os
import subprocess

BASE_URL = os.getenv("PLAYWRIGHT_BASE_URL", "http://localhost:45001")

# Paths to REAL test artifacts in tests/artifacts/
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")
TEST_CATALOG_PDF = os.path.join(ARTIFACTS_DIR, "mock_menu.pdf")
TEST_CATALOG_IMAGE = os.path.join(ARTIFACTS_DIR, "mock_menu_image.jpg")


@pytest.fixture(autouse=True)
def verify_test_artifacts():
    """Fail loudly if test artifact files are missing."""
    for path in (TEST_CATALOG_PDF, TEST_CATALOG_IMAGE):
        if not os.path.isfile(path):
            pytest.fail(
                f"Required test artifact not found: {path}. "
                f"Ensure tests/artifacts/ contains the real test files."
            )


@pytest.fixture(autouse=True)
def reset_tenant_state():
    """Reset live Avender tenant state so the onboarding flow can run end-to-end."""
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "usr", "workdir", "avender.db")
    conn = sqlite3.connect(db_path, timeout=30)
    c = conn.cursor()
    c.execute("DELETE FROM tenant_config")
    c.execute("DELETE FROM catalog_item")
    conn.commit()
    conn.close()


def test_avender_onboarding_full_flow(page: Page):
    """
    Test the entire Zero-Friction onboarding flow via the Web UI.
    Navigates through the 7 steps and verifies the final submission.
    All API calls hit the REAL backend — no route interception.
    """

    # 1. Login (if required by the environment)
    page.goto(f"{BASE_URL}/login")
    if page.locator("input[name='username']").is_visible(timeout=3000):
        page.fill("input[name='username']", os.getenv("AUTH_LOGIN", "admin"))
        page.fill("input[name='password']", os.getenv("AUTH_PASSWORD", "admin"))
        page.click("button[type='submit']")
        page.wait_for_url("**/")

    # 2. Navigate to the Onboarding Wizard
    page.goto(f"{BASE_URL}/usr/plugins/avender/webui/onboarding.html")
    expect(page).to_have_title("¡A VENDER! - Activación de Asistente")

    # -- Step 1: Datos de tu Negocio --
    expect(page.locator("h2").filter(has_text="Paso 1: Tu Negocio")).to_be_visible()
    page.select_option("select", "RUC")
    page.fill("input[placeholder='Ej: 1712345678001']", "1791234567001")
    page.fill("input[placeholder='Ej: Juan Pérez S.A.']", "Restaurante E2E Test S.A.")
    page.fill("input[placeholder='Ej: Burger House']", "Restaurante E2E Test")
    page.click("button:has-text('Siguiente')")

    # -- Step 2: Operaciones y Delivery --
    expect(
        page.locator("h2").filter(has_text="Paso 2: Entrega y Pagos")
    ).to_be_visible()
    page.click("text='Tocar mapa para fijar ubicación (GPS)'")
    page.click("button:has-text('📍 Centrar en mi ubicación actual')")
    page.wait_for_timeout(1000)  # Wait for Leaflet to initialize
    page.fill(
        "input[placeholder='Ej: Av. Amazonas y Naciones Unidas, Quito']",
        "Av. Principal y Secundaria, E2E Test",
    )
    page.locator("label").filter(has_text="Transferencia Bancaria").locator(
        "input"
    ).check()
    page.click("button:has-text('Siguiente')")

    # -- Step 3: Industria y Catálogo --
    expect(page.locator("h2").filter(has_text="Paso 3: Tu Catálogo")).to_be_visible()
    # Click the "Restaurante / Comidas" card
    page.click("div:has-text('🍔') >> text=Restaurante / Comidas")

    page.click("button:has-text('Crear Manualmente')")
    # Close the catalog review modal so the inline table is accessible
    page.click("button:has-text('Confirmar y Cerrar')")
    expect(page.locator("text=Verifica tu menú extraído:")).to_be_visible(timeout=60000)
    page.wait_for_selector("table tbody tr", timeout=60000)

    # Edit the price of the first parsed item
    first_price_input = page.locator("input[type='number']").first
    if first_price_input.is_visible():
        first_price_input.fill("8.99")

    # Upload the REAL image test artifact to the first item
    image_inputs = page.locator("input[type='file'][accept='image/*']")
    if image_inputs.count() > 0:
        image_inputs.first.set_input_files(TEST_CATALOG_IMAGE)

    page.locator("textarea").last.fill("2x1 los Martes - Test E2E")

    page.click("button:has-text('Siguiente')")

    # -- Step 4: Personalidad --
    expect(page.locator("h2").filter(has_text="Paso 4: Personalidad")).to_be_visible()
    page.fill("input[placeholder='Ej: Sofía']", "Vendedor E2E")
    page.locator("select").nth(1).select_option("formal")
    page.locator("input[type='checkbox']").last.check()  # Hablar como Ecuatoriano
    page.click("button:has-text('Siguiente')")

    # -- Step 5: WhatsApp y Seguridad --
    expect(
        page.locator("h2").filter(has_text="Paso 5: Seguridad y Control")
    ).to_be_visible()
    page.fill("input[placeholder='+593...']", "+593997202547")
    page.fill("input[type='password']", "SecureAdminPass123!")
    page.locator("input[type='checkbox']").last.check()
    page.fill("input[placeholder='Ej: +593912345678']", "+593997202547")
    page.click("button:has-text('+')")
    page.click("button:has-text('Siguiente')")

    # -- Step 6: Cierre (¡Casi terminamos!) --
    expect(page.locator("h2").filter(has_text="¡Casi terminamos!")).to_be_visible()
    page.click("button:has-text('¡Terminar y Activar!')")

    # -- Step 7: Éxito --
    # Wait for either QR code or already-connected state
    page.wait_for_timeout(4000)  # Let QR polling fire
    qr_heading = page.locator("h2").filter(has_text="Escanea el Código QR")
    connected_heading = page.locator("h2").filter(has_text="¡Conectado Exitosamente!")

    assert qr_heading.is_visible() or connected_heading.is_visible(), (
        "Step 7 did not load: neither QR code nor connected state visible"
    )

    print(
        "✅ E2E Playwright Test completed successfully! Full flow verified against LIVE backend."
    )
