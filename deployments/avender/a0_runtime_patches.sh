#!/bin/bash
# ============================================================================
# ¡A VENDER! — Agent Zero Runtime Patches
# ============================================================================
# Applies fixes to third-party packages inside the Agent Zero container.
# These patches address upstream bugs that have not been fixed yet.
# Mounted and executed via docker-compose.dev.yml.
# ============================================================================
set -e

# --- Fix 1: SearxNG wikidata engine KeyError on 'name' key ---------------
# Upstream issue: wikidata.py assumes result dict always has 'name'.
# Some Wikidata SPARQL responses omit the field, crashing the init.
WIKIDATA_FILE='/usr/local/searxng/searx-pyenv/lib/python3.13/site-packages/searx/engines/wikidata.py'
if [ -f "$WIKIDATA_FILE" ]; then
    if grep -q "result\['name'\]\['value'\]" "$WIKIDATA_FILE"; then
        sed -i "s/name = result\['name'\]\['value'\]/name = result.get('name', {}).get('value', '')/" "$WIKIDATA_FILE"
        echo "[a0-patches] FIXED: SearxNG wikidata KeyError"
    fi
fi

# --- Fix 2: Suppress authlib deprecation warning in fastmcp ---------------
# fastmcp uses authlib.jose which is deprecated in favor of joserfc.
# This is cosmetic — authlib remains functional until v2.0.
FASTMCP_JWT='/opt/venv-a0/lib/python3.12/site-packages/fastmcp/server/auth/providers/jwt.py'
if [ -f "$FASTMCP_JWT" ]; then
    if ! grep -q 'import warnings' "$FASTMCP_JWT"; then
        sed -i '1i import warnings\nwarnings.filterwarnings("ignore", category=DeprecationWarning, module="authlib")' "$FASTMCP_JWT"
        echo "[a0-patches] FIXED: authlib deprecation warning suppressed"
    fi
fi
