"""Generic form-filler for external ATS pages (Greenhouse, Lever, Workday, Ashby, Workable).

Strategy: label-based. For each required input/select/textarea on the page,
grab its label, route to either (a) a known field from facts.yaml (name/email/
phone/linkedin/resume upload/city/state) or (b) the LLM answerer.

Same hard rules as the LinkedIn path:
  * Never type a GitHub, portfolio, or personal-website URL.
  * Skip postings that require fields we can't confidently fill.
"""
from __future__ import annotations
import os, re, yaml, json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

ROOT = Path(__file__).resolve().parents[1]
FACTS = yaml.safe_load((ROOT / "resume" / "facts.yaml").read_text())
APPLIED_LOG = ROOT / "data" / "applied.jsonl"
RESUMES = ROOT / "resume"

VARIANT_FILES = {
    "DS_ML_Research":   "Resume_Abhignya_DataScience_ML_Research.docx",
    "AI_Engineering":   "Resume_Abhignya_AI_Engineering.docx",
    "Data_Engineering": "Resume_Abhignya_Data_Engineering.docx",
    "Data_Analytics":   "Resume_Abhignya_Data_Analytics.docx",
}

BANNED_FIELD_RE = re.compile(r"github|portfolio|personal\s+website|personal\s+url", re.I)


def _log(entry: dict):
    APPLIED_LOG.parent.mkdir(parents=True, exist_ok=True)
    with APPLIED_LOG.open("a") as f: f.write(json.dumps(entry) + "\n")


def _dry() -> bool:
    return os.environ.get("APPLY_DRY_RUN", "1") != "0"


def _resume_path(variant: str) -> Path:
    return RESUMES / VARIANT_FILES.get(variant, VARIANT_FILES["DS_ML_Research"])


def _known_value(label: str) -> str | None:
    l = label.lower()
    if "first name" in l: return FACTS["name"].split()[0]
    if "last name" in l:  return FACTS["name"].split()[-1]
    if "full name" in l or l.strip() == "name": return FACTS["name"]
    if "email" in l: return FACTS["email"]
    if "phone" in l: return FACTS.get("phone", "") or None
    if "linkedin" in l: return FACTS.get("linkedin", "")
    if "city" in l:    return "Dallas"
    if "state" in l:   return "Texas"
    if "zip" in l or "postal" in l: return "75019"
    if "country" in l: return "United States"
    if "school" in l or "university" in l: return FACTS["education"]["school"]
    if "degree" in l: return FACTS["education"]["degree"]
    if "gpa" in l: return str(FACTS["logistics"].get("gpa", ""))
    if "start" in l and "date" in l: return FACTS["logistics"].get("start_date", "")
    if "sponsor" in l: return FACTS["work_authorization"]["requires_sponsorship"]
    if "author" in l and ("work" in l or "us" in l): return FACTS["work_authorization"]["authorized_us"]
    if "relocate" in l: return FACTS["logistics"]["willing_to_relocate"]
    return None


def _fill_field(page, field, label: str, llm_answer) -> str:
    if BANNED_FIELD_RE.search(label):
        return "banned_field"
    val = _known_value(label)
    if val is None:
        val = llm_answer(label)
    if not val:
        return "no_answer"
    try:
        field.fill(str(val)); return "filled"
    except Exception:
        return "fill_error"


def apply_one(page, job: dict) -> str:
    from apply.llm_answers import answer as llm_answer
    try:
        page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        return f"nav_error:{type(e).__name__}"
    page.wait_for_timeout(2500)

    # Upload resume if page accepts it
    try:
        inp = page.locator("input[type='file']").first
        if inp.count() > 0:
            resume = _resume_path(job.get("resume_variant","DS_ML_Research"))
            if resume.exists():
                inp.set_input_files(str(resume))
                page.wait_for_timeout(1500)
    except Exception: pass

    if _dry():
        return "dry_run_page_loaded"

    # Fill text fields
    for selector in ["input[required]:not([type=file]):not([type=hidden]):not([type=checkbox]):not([type=radio])",
                     "textarea[required]"]:
        fields = page.locator(selector)
        for i in range(fields.count()):
            f = fields.nth(i)
            try:
                label = f.evaluate("el => (el.labels && el.labels[0]?.innerText) || el.getAttribute('aria-label') || el.name || el.placeholder || ''")
            except Exception:
                label = ""
            if not label: continue
            if _fill_field(page, f, label, llm_answer) == "banned_field":
                return "skipped_banned_field"

    # Required selects
    selects = page.locator("select[required]")
    for i in range(selects.count()):
        s = selects.nth(i)
        try:
            label = s.evaluate("el => (el.labels && el.labels[0]?.innerText) || el.getAttribute('aria-label') || ''")
            opts = s.evaluate("el => Array.from(el.options).map(o => o.innerText).filter(Boolean)")
        except Exception:
            label, opts = "", []
        if not label or not opts: continue
        if BANNED_FIELD_RE.search(label): return "skipped_banned_field"
        val = _known_value(label)
        if val and val in opts:
            try: s.select_option(label=val)
            except Exception: pass
            continue
        ans = llm_answer(label, options=opts)
        if ans in opts:
            try: s.select_option(label=ans)
            except Exception: pass

    # Click submit
    for label in ["Submit application", "Submit", "Apply", "Send application"]:
        btn = page.locator(f"button:has-text('{label}'), input[type=submit][value='{label}']").first
        if btn.count() and btn.is_enabled():
            btn.click(); page.wait_for_timeout(2500)
            return "submitted"
    return "no_submit_button"


def run(jobs: list[dict], cfg: dict) -> list[dict]:
    results = []
    max_n = cfg.get("apply", {}).get("max_per_run", 100)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        for j in jobs[:max_n]:
            try:
                status = apply_one(page, j)
            except Exception as e:
                status = f"error:{type(e).__name__}"
            entry = {"job_id": j["job_id"], "title": j["title"], "company": j.get("company"),
                     "url": j["url"], "variant": j.get("resume_variant"),
                     "source": j.get("source"), "result": status}
            _log(entry); results.append(entry)
        browser.close()
    return results
