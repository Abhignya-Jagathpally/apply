"""LinkedIn scraper. Uses Playwright + saved auth state.

Handles both short URLs (lnkd.in/...) — which redirect to saved searches —
and canonical /jobs/search?... URLs.
"""
from __future__ import annotations
import json, os, re
from pathlib import Path
from playwright.sync_api import sync_playwright

STATE = Path(__file__).resolve().parents[1] / "data" / "li_state.json"


def _ensure_state():
    # In CI, decode LINKEDIN_STATE_JSON env into the file
    env = os.environ.get("LINKEDIN_STATE_JSON")
    if env and not STATE.exists():
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(env)


def fetch_jobs(urls: list[str]) -> list[dict]:
    _ensure_state()
    if not STATE.exists():
        print("[linkedin] no auth state — skipping")
        return []
    jobs: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=str(STATE),
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36")
        page = ctx.new_page()
        for url in urls:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3500)
                # scroll to lazy-load
                for _ in range(5):
                    page.mouse.wheel(0, 3000); page.wait_for_timeout(600)
                cards = page.locator("div.job-card-container, li.jobs-search-results__list-item")
                n = cards.count()
                for i in range(n):
                    c = cards.nth(i)
                    try:
                        title = c.locator("a.job-card-list__title, a.job-card-container__link").first.inner_text(timeout=1500).strip()
                        href = c.locator("a.job-card-list__title, a.job-card-container__link").first.get_attribute("href") or ""
                        company = c.locator(".artdeco-entity-lockup__subtitle, .job-card-container__primary-description").first.inner_text(timeout=1500).strip()
                        loc = c.locator(".job-card-container__metadata-item, .artdeco-entity-lockup__caption").first.inner_text(timeout=1500).strip()
                    except Exception:
                        continue
                    m = re.search(r"/jobs/view/(\d+)", href)
                    jid = f"linkedin:{m.group(1)}" if m else f"linkedin:{href}"
                    easy = False
                    try:
                        easy = "Easy Apply" in c.inner_text(timeout=1000)
                    except Exception: pass
                    jobs.append({
                        "source": "linkedin",
                        "job_id": jid,
                        "title": title, "company": company, "location": loc,
                        "remote": "remote" in loc.lower(),
                        "url": href if href.startswith("http") else f"https://www.linkedin.com{href}",
                        "easy_apply": easy,
                    })
            except Exception as e:
                print(f"[linkedin] {url} failed: {e}")
        browser.close()
    return jobs
