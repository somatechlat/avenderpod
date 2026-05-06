import re
import os

with open('admin/tenants/static/tenants/js/dashboard.js', 'r') as f:
    js_code = f.read()

# Extract Sidebar
sidebar_match = re.search(r'renderSidebar\(\) \{(.*?)\s*return html`(.*?)`;\s*\}', js_code, re.DOTALL)
if sidebar_match:
    sidebar_html = f"return html`{sidebar_match.group(2)}`;"
    sidebar_logic = sidebar_match.group(1).strip()
    js_code = js_code.replace(sidebar_match.group(0), "${renderSidebar.call(this)}")
    
    with open('admin/tenants/static/tenants/js/sidebar-render.js', 'w') as f:
        f.write("import { html } from 'https://cdn.jsdelivr.net/npm/lit@3.1.2/+esm';\n")
        f.write("export function renderSidebar() {\n")
        if sidebar_logic:
            f.write("    " + sidebar_logic + "\n")
        f.write("    " + sidebar_html + "\n")
        f.write("}\n")

# Extract Dashboard
dashboard_match = re.search(r'renderDashboard\(\) \{\s*return html`(.*?)`;\s*\}', js_code, re.DOTALL)
if dashboard_match:
    dashboard_html = f"return html`{dashboard_match.group(1)}`;"
    js_code = js_code.replace(dashboard_match.group(0), "${renderDashboard.call(this)}")
    
    with open('admin/tenants/static/tenants/js/dashboard-render.js', 'w') as f:
        f.write("import { html } from 'https://cdn.jsdelivr.net/npm/lit@3.1.2/+esm';\n")
        f.write("export function renderDashboard() {\n")
        f.write("    " + dashboard_html + "\n")
        f.write("}\n")

# Update imports
imports = """import { renderSidebar } from './sidebar-render.js';
import { renderDashboard } from './dashboard-render.js';
"""
js_code = js_code.replace("import { renderPlanWizard", imports + "import { renderPlanWizard")

with open('admin/tenants/static/tenants/js/dashboard.js', 'w') as f:
    f.write(js_code)

print("Extraction 2 successful.")
