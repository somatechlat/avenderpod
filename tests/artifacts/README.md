# ¡A VENDER! Testing Artifacts

This directory contains mock files and generation scripts used strictly for testing the catalog parsing and ingestion logic. **Do not use these files in production.**

## Files Included

| File | Purpose |
|------|---------|
| `mock_catalog.xlsx` | A test Excel catalog containing simulated products, prices, and descriptions to test the `parse_catalog_api`. |
| `mock_menu.pdf` | A test PDF menu containing simulated restaurant items to verify the Agent's multimodal PDF text extraction. |
| `mock_menu_image.jpg` | A test JPEG image of a menu to verify the Agent's OCR capabilities (using Gemini/GPT-4o vision) during the Onboarding Wizard. |
| `create_test_xls.py` | A Python script used to dynamically generate or regenerate the `mock_catalog.xlsx` file for unit testing. |

## Usage
These files are automatically referenced by the E2E Playwright tests and unit tests within the `tests/e2e/` folder. If you need to manually test the onboarding file upload logic, you may select these files when prompted by the web UI.
