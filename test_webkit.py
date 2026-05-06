from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.webkit.launch()
        page = browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(err))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        print("Navigating to http://localhost:45000/")
        page.goto("http://localhost:45000/login/")
        page.fill('input[name="username"]', 'admin')
        page.fill('input[name="password"]', 'admin123') # assuming admin123, wait, test_real_e2e.sh uses Vault password
        
        # let's just go to the dashboard URL directly if it redirects, wait, it requires login.
        # But we can capture the login page errors first.
        browser.close()
        for e in errors:
            print("ERROR:", e)

run()
