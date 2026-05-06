import re
import os

with open('admin/tenants/templates/tenants/dashboard.html', 'r') as f:
    content = f.read()

# Extract the script block
script_match = re.search(r'<script type="module">(.*?)</script>', content, re.DOTALL)
if not script_match:
    print("No script block found")
    exit(1)

js_code = script_match.group(1)

# We will just write the JS code to admin/tenants/static/tenants/js/dashboard.js
# But wait, it's 800 lines. The user said NO FILE > 590 lines.
# So dashboard.js will be split.
# I'll let the Python script do it later if needed, but actually I can just run it to extract it first.
