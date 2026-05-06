import re
import os

with open('admin/tenants/templates/tenants/dashboard.html', 'r') as f:
    content = f.read()

# Extract script block
script_match = re.search(r'<script type="module">(.*?)</script>', content, re.DOTALL)
js_code = script_match.group(1)

# Extract Tenant Wizard
tenant_wizard_match = re.search(r'<!-- WIZARD OVERLAY -->(.*?)<!-- PLAN WIZARD OVERLAY', js_code, re.DOTALL)
tenant_wizard_html = tenant_wizard_match.group(1).strip()
# Remove the wrapping `${this.showWizard ? html` and ` : ''}`
tenant_wizard_html = tenant_wizard_html.replace('${this.showWizard ? html`', 'return this.showWizard ? html`')
# The end has ` : ''}` which we want to turn into ` : html\`\`;`
tenant_wizard_html = re.sub(r"` : ''}$", "` : '';", tenant_wizard_html)

# Extract Plan Wizard
plan_wizard_match = re.search(r'<!-- PLAN WIZARD OVERLAY \(3-Column\) -->(.*?)</div>\s*`;', js_code, re.DOTALL)
plan_wizard_html = plan_wizard_match.group(1).strip()
plan_wizard_html = plan_wizard_html.replace('${this.showPlanWizard ? html`', 'return this.showPlanWizard ? html`')
plan_wizard_html = re.sub(r"` : ''}$", "` : '';", plan_wizard_html)

# Now we need to remove them from the original js_code
new_js_code = js_code.replace(tenant_wizard_match.group(0), "${renderTenantWizard.call(this)}\n                        <!-- PLAN WIZARD OVERLAY")
new_js_code = new_js_code.replace(plan_wizard_match.group(0), "${renderPlanWizard.call(this)}\n                    </div>\n                `;")

# Add imports to the top of new_js_code
new_js_code = """
import { renderPlanWizard } from './plan-wizard-render.js';
import { renderTenantWizard } from './tenant-wizard-render.js';
""" + new_js_code.strip()

# Create the JS files
os.makedirs('admin/tenants/static/tenants/js', exist_ok=True)

with open('admin/tenants/static/tenants/js/dashboard.js', 'w') as f:
    f.write(new_js_code)

with open('admin/tenants/static/tenants/js/plan-wizard-render.js', 'w') as f:
    f.write("import { html } from 'https://cdn.jsdelivr.net/npm/lit@3.1.2/+esm';\n")
    f.write("export function renderPlanWizard() {\n")
    f.write(plan_wizard_html)
    f.write("\n}\n")

with open('admin/tenants/static/tenants/js/tenant-wizard-render.js', 'w') as f:
    f.write("import { html } from 'https://cdn.jsdelivr.net/npm/lit@3.1.2/+esm';\n")
    f.write("export function renderTenantWizard() {\n")
    f.write(tenant_wizard_html)
    f.write("\n}\n")

# Replace script block in HTML
new_html = content[:script_match.start()] + '<script type="module" src="{% static \'tenants/js/dashboard.js\' %}"></script>' + content[script_match.end():]

with open('admin/tenants/templates/tenants/dashboard.html', 'w') as f:
    f.write(new_html)

print("Extraction successful.")
