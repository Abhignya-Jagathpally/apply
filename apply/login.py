"""Run locally once to capture LinkedIn auth state.

    python -m apply.login

Opens a real Chromium window, you log in, press Enter in the terminal,
the cookies are saved to data/li_state.json. Then add that file's contents
as the GitHub Actions secret LINKEDIN_STATE_JSON.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

STATE = Path(__file__).resolve().parents[1] / "data" / "li_state.json"

def main():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto("https://www.linkedin.com/login")
        input("Log in in the opened window, then press Enter here to save cookies... ")
        ctx.storage_state(path=str(STATE))
        print(f"Saved {STATE}")
        browser.close()

if __name__ == "__main__":
    main()
