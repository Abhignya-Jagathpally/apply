# apply — Daily Data/AI Internship Auto-Apply Pipeline

Automates discovery and application to **Data and AI internships** in:
- Dallas–Fort Worth, TX (and surrounding cities)
- Remote, anywhere in USA

Runs daily via GitHub Actions. Aggregates from LinkedIn, Greenhouse, Lever, Workday,
and Ashby. De-duplicates, filters intelligently, and submits applications using
saved browser session cookies.

> **Note:** Personal GitHub project URLs are intentionally excluded from every
> application per the owner's preference.

## Layout

```
scrapers/     source-specific scrapers (linkedin, greenhouse, lever, workday, ashby)
filters/      keyword + location + role-type + seniority filters, dedupe
apply/        application submitters (linkedin easy-apply, ATS form-fillers)
resume/       4 resume variants + mapping logic (DS/ML, AI Eng, Data Eng, Analytics)
data/         jobs.jsonl (dedup store), applied.jsonl (audit log)
.github/      daily cron workflow
```

## Saved LinkedIn searches

The pipeline includes three user-provided LinkedIn saved searches:

- https://lnkd.in/dyQjDeZq
- https://lnkd.in/dajwvFXq
- https://lnkd.in/djTA9mSf

They are resolved at runtime via Playwright (requires an authenticated session — see
Setup). A canonical fallback search is also run so the pipeline keeps working even if
a saved search expires.

## Setup

1. `pip install -r requirements.txt && playwright install chromium`
2. Run `python -m apply.login` once locally to create `data/li_state.json`
   (stores your LinkedIn auth cookies).
3. Add the contents of `data/li_state.json` as the GitHub Actions secret
   `LINKEDIN_STATE_JSON`.
4. Push. The daily workflow (`.github/workflows/daily.yml`) runs at 13:00 UTC.

## Filtering logic (the "smart" bit)

A job passes the filter when **all** of:

- Title matches data/AI intent: `(data|ml|ai|machine learning|analytics|scientist|engineer|research)` AND `(intern|internship|co-?op)`
- Location is Dallas-area OR Remote-USA (see `filters/location.py`)
- Seniority is intern / early-career (excludes senior, staff, principal, lead)
- Title does not hit the negative list (sales, marketing, finance-only, recruiter)
- Not already in `data/applied.jsonl`

Each surviving job is routed to the best-matching resume variant
(DS_ML_Research / AI_Engineering / Data_Engineering / Data_Analytics).

## Safety

- Dry-run by default (`APPLY_DRY_RUN=1`). Set to `0` in workflow env to actually submit.
- Skips any posting whose page contains a free-text "GitHub" or "portfolio URL"
  required field — per owner preference.
- Logs every action to `data/applied.jsonl`.
