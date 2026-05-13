"""
E2E Test Configuration — ¡A VENDER! SysAdmin Control Plane

Shared fixtures and configuration for all Playwright E2E tests.
"""

import os

try:
    import pytest
    _HAS_E2E_DEPS = True
except ImportError:
    pytest = None
    _HAS_E2E_DEPS = False

# ── Base URL for all E2E tests ───────────────────────────────────────────
SYSADMIN_URL = os.environ.get("SYSADMIN_URL", "http://localhost:45000")


if _HAS_E2E_DEPS:
    @pytest.fixture(scope="session")
    def browser_context_args(browser_context_args):
        """Allow self-signed certs in dev environments."""
        return {
            **browser_context_args,
            "ignore_https_errors": True,
        }

    @pytest.fixture(scope="session")
    def base_url():
        """Return the base URL for the SysAdmin service."""
        return SYSADMIN_URL
