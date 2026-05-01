"""
Integration tests for catalog parsing via the live parse_catalog_api endpoint.
Tests real file uploads (PDF, XLSX, CSV) against the running Agent Zero instance.
"""

import base64
import os
import requests

BASE_URL = os.getenv("PLAYWRIGHT_BASE_URL", "http://localhost:45001")
API_URL = f"{BASE_URL}/api/plugins/avender/parse_catalog_api"
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


def _upload_file(path: str, archetype: str = "restaurant") -> dict:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(path)[1].lower()
    mime = {
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }.get(ext, "application/octet-stream")
    payload = {
        "catalogFile": {
            "name": os.path.basename(path),
            "content": f"data:{mime};base64,{b64}",
        },
        "archetype": archetype,
    }
    resp = requests.post(API_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def test_santa_lucia_pdf_parses_with_known_items():
    """Santa Lucia is a real bilingual restaurant menu PDF."""
    path = os.path.join(ARTIFACTS_DIR, "santa-lucia.pdf")
    assert os.path.isfile(path), f"Missing test artifact: {path}"

    data = _upload_file(path, archetype="restaurant")
    assert data["ok"] is True, f"Parse failed: {data.get('error')}"

    items = data.get("items", [])
    assert len(items) > 10, f"Expected many items from a full menu, got {len(items)}"

    names = [it["name"].lower() for it in items]
    # Known dishes from the Santa Lucia menu (Spanish versions)
    assert any("ceviche santa lucia" in n for n in names), "Missing signature dish"
    assert any("scallops" in n for n in names), "Missing scallops dish"
    assert any("tiramis" in n for n in names), "Missing tiramisu dessert"

    # Verify prices are floats and reasonable
    prices = [it["price"] for it in items if isinstance(it.get("price"), (int, float))]
    assert all(p > 0 for p in prices), "All prices must be positive"
    assert all(p < 1000 for p in prices), "Prices should be under 1000"


def test_mock_catalog_xlsx_parses_correctly():
    """Excel with explicit Producto/Precio columns."""
    path = os.path.join(ARTIFACTS_DIR, "mock_catalog.xlsx")
    assert os.path.isfile(path), f"Missing test artifact: {path}"

    data = _upload_file(path, archetype="cbd")
    assert data["ok"] is True, f"Parse failed: {data.get('error')}"

    items = data.get("items", [])
    assert len(items) == 4, f"Expected 4 CBD items, got {len(items)}"

    names = [it["name"] for it in items]
    assert "Aceite de CBD 500mg" in names
    assert "Gomitas Relajantes" in names

    prices = {it["name"]: it["price"] for it in items}
    assert prices["Aceite de CBD 500mg"] == 25.5
    assert prices["Gomitas Relajantes"] == 15.0


def test_csv_catalog_parses_correctly():
    """CSV with Producto,Precio,Descripcion columns."""
    csv_path = "/tmp/test_catalog_integration.csv"
    with open(csv_path, "w") as f:
        f.write("Producto,Precio,Descripcion\n")
        f.write("Empanada de Queso,2.50,Con salsa\n")
        f.write("Hamburguesa Clasica,8.00,Con papas\n")
        f.write("Gaseosa 500ml,1.50,Coca o Sprite\n")

    data = _upload_file(csv_path, archetype="restaurant")
    assert data["ok"] is True, f"Parse failed: {data.get('error')}"

    items = data.get("items", [])
    assert len(items) == 3, f"Expected 3 items, got {len(items)}"

    names = [it["name"] for it in items]
    assert "Empanada de Queso" in names
    assert "Hamburguesa Clasica" in names
    assert "Gaseosa 500ml" in names


def test_dummy_pdf_returns_empty_gracefully():
    """A PDF with no menu data should return 0 items without crashing."""
    path = os.path.join(ARTIFACTS_DIR, "mock_menu.pdf")
    assert os.path.isfile(path), f"Missing test artifact: {path}"

    data = _upload_file(path, archetype="restaurant")
    # The dummy PDF only contains "Dummy PDF file" text
    # The parser may return ok=True with 0 items or ok=False with an error
    assert data.get("ok") is True or "claridad" in (data.get("error") or "")
    assert len(data.get("items", [])) == 0
