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
    
    # Mock the catalog parsing endpoint to return 2 fake items when the PDF is uploaded
    page.route("**/api/plugins/avender/parse_catalog_api", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"ok": true, "items": [{"name": "Hamburguesa Doble", "price": "7.50"}, {"name": "Papas Medianas", "price": "2.50"}]}'
    ))

    page.goto(f"{BASE_URL}/usr/plugins/avender/webui/onboarding.html")
    expect(page).to_have_title("¡A VENDER! - Activación de Asistente")

    # -- Step 1: Datos de tu Negocio --
    expect(page.locator("h2").filter(has_text="Paso 1: Tu Negocio")).to_be_visible()
    page.fill("input[placeholder='Ej: Juan Pérez S.A.']", "Restaurante E2E Test")
    page.select_option("select", "RUC")
    page.fill("input[placeholder='Ej: 1712345678001']", "1791234567001")
    page.click("button:has-text('Siguiente')")

    # -- Step 2: Operaciones y Delivery --
    expect(page.locator("h2").filter(has_text="Paso 2: Entrega y Pagos")).to_be_visible()
    # Click to use current location (mocked or just click)
    page.click("text='Tocar mapa para fijar ubicación (GPS)'")
    page.click("button:has-text('📍 Centrar en mi ubicación actual')")
    page.wait_for_timeout(1000) # Wait for Leaflet to catch up
    page.fill("textarea", "Av. Principal y Secundaria, E2E Test")
    page.click("button:has-text('Siguiente')")

    # -- Step 3: Industria y Catálogo --
    expect(page.locator("h2").filter(has_text="Paso 3: Tu Catálogo")).to_be_visible()
    # Click the "Restaurante / Comidas" card
    page.click("div:has-text('🍔') >> text=Restaurante / Comidas")
    
    # Create a mock PDF file to upload
    with open("mock_catalog.pdf", "w") as f:
        f.write("Mock PDF Content")
    
    # Upload the PDF
    page.set_input_files("input[type='file'][id='file-upload']", "mock_catalog.pdf")
    # Wait for the table headers to appear instead of waiting for a mock item
    expect(page.locator("text=Verifica tu menú extraído:")).to_be_visible()
    
    # Check if there are products, if not, wait
    page.wait_for_selector("table tbody tr")
    
    # Edit the price of the first item
    page.fill("input[type='number'] >> nth=0", "8.99")
    
    # Create a mock image file to upload
    with open("mock_image.jpg", "w") as f:
        f.write("Mock Image Content")

    # Upload the image to the first item
    page.set_input_files("input[type='file'][accept='image/*'] >> nth=0", "mock_image.jpg")
    
    page.fill("textarea[placeholder='Escribe tus promociones aquí...']", "2x1 los Martes")
    
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
