"""LinkedIn Easy Apply submitter.

Safety:
  * Dry-run by default.
  * Skips any posting that requires a GitHub/portfolio URL free-text field.
  * Never fills unknown free-text questions; skips instead.
"""
from __future__ import annotations
import os, re, json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "li_state.json"
APPLIED_LOG = ROOT / "data" / "applied.jsonl"
RESUMES = ROOT / "resume"

def _log(entry: dict):
    APPLIED_LOG.parent.mkdir(parents=True, exist_ok=True)
    with APPLIED_LOG.open("a") as f: f.write(json.dumps(entry) + "\n")

def _dry() -> bool:
    return os.environ.get("APPLY_DRY_RUN", "1") != "0"

def _resume_path(variant: str) -> Path:
    # matches filenames produced by resume/ builder
    mapping = {
        "DS_ML_Research": "Resume_Abhignya_DataScience_ML_Research.docx",
        "AI_Engineering": "Resume_Abhignya_AI_Engineering.docx",
        "Data_Engineering": "Resume_Abhignya_Data_Engineering.docx",
        "Data_Analytics": "Resume_Abhignya_Data_Analytics.docx",
    }
    return RESUMES / mapping.get(variant, mapping["DS_ML_Research"])

def _has_forbidden_field(page, skip_terms) -> bool:
    text = page.inner_text("body").lower()
    return any(term in text for term in skip_terms)

def apply_one(page, job: dict, skip_terms: list[str]) -> str:
    page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2500)
    # Click Easy Apply
    try:
        page.locator("button:has-text('Easy Apply')").first.click(timeout=5000)
    except PWTimeout:
        return "no_easy_apply"
    page.wait_for_timeout(1500)

    if _has_forbidden_field(page, skip_terms):
        page.keyboard.press("Escape"); return "skipped_forbidden_field"

    # Upload resume if an upload control is present
    try:
        resume = _resume_path(job.get("resume_variant","DS_ML_Research"))
        if resume.exists():
            inp = page.locator("input[type='file']").first
            if inp.count() > 0: inp.set_input_files(str(resume))
    except Exception: pass

    # Walk the wizard: Next -> Next -> Review -> Submit
    for _ in range(8):
        if _dry():
            page.keyboard.press("Escape"); return "dry_run_walkthrough_ok"
        # Any unanswered required free-text? bail.
        unanswered = page.locator("input[required]:not([value]), textarea[required]:empty")
        if unanswered.count() > 0:
            page.keyboard.press("Escape"); return "skipped_unanswered_required"
        # Click the most advanced available button
        for label in ["Submit application", "Review", "Next"]:
            btn = page.locator(f"button:has-text('{label}')").first
            if btn.count() and btn.is_enabled():
                btn.click(); page.wait_for_timeout(1200)
                if label == "Submit application":
                    return "submitted"
                break
        else:
            return "stuck_in_wizard"
    return "wizard_too_long"


def run(jobs: list[dict], cfg: dict) -> list[dict]:
    results = []
    skip_terms = cfg.get("apply", {}).get("skip_if_asks_for", [])
    max_n = cfg.get("apply", {}).get("max_per_run", 25)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=str(STATE) if STATE.exists() else None)
        page = ctx.new_page()
        for j in jobs[:max_n]:
            if not j.get("easy_apply"):
                results.append({**j, "result": "non_easy_apply_needs_manual"}); continue
            try:
                status = apply_one(page, j, skip_terms)
            except Exception as e:
                status = f"error:{type(e).__name__}"
            entry = {"job_id": j["job_id"], "title": j["title"], "company": j.get("company"),
                     "url": j["url"], "variant": j.get("resume_variant"), "result": status}
            _log(entry); results.append(entry)
        browser.close()
    return results
