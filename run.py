"""Main pipeline entrypoint. Run daily.

  python run.py
"""
from __future__ import annotations
import json, yaml
from pathlib import Path
from scrapers.jobspy_source import fetch as jobspy_fetch
from scrapers.linkedin import fetch_jobs as li_fetch       # kept for saved-search URLs
from scrapers.ats import greenhouse, lever, ashby, workable, smartrecruiters, breezy
from scrapers.custom_boards import fetch_all as custom_fetch
from filters.smart import filter_jobs
from apply.linkedin_easy_apply import run as li_apply
from apply.generic_ats import run as ats_apply

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"; DATA.mkdir(exist_ok=True)

def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())

    jobs: list[dict] = []
    # Primary multi-board aggregator
    jobs += jobspy_fetch(cfg)
    # Keep the saved-search Playwright path so your three lnkd.in/... URLs still feed in
    jobs += li_fetch(cfg["linkedin_saved_searches"])
    # ATS boards (direct company career pages)
    for slug in cfg.get("greenhouse_slugs", []):      jobs += greenhouse(slug)
    for slug in cfg.get("lever_slugs", []):           jobs += lever(slug)
    for slug in cfg.get("ashby_slugs", []):           jobs += ashby(slug)
    for slug in cfg.get("workable_slugs", []):        jobs += workable(slug)
    for slug in cfg.get("smartrecruiters_slugs", []): jobs += smartrecruiters(slug)
    for slug in cfg.get("breezy_slugs", []):          jobs += breezy(slug)
    # Custom boards (Dice, SimplyHired, YC, Zintellect)
    jobs += custom_fetch()

    print(f"[run] raw jobs: {len(jobs)}")
    # show a sample so we can sanity-check what the scrapers brought in
    for j in jobs[:20]:
        print(f"  [sample] {j.get('source','?'):22} | {j.get('location','')[:40]:40} | {j.get('title','')[:80]}")
    (DATA / "jobs.jsonl").write_text("\n".join(json.dumps(j) for j in jobs))

    matched = filter_jobs(jobs, cfg)
    print(f"[run] after filter: {len(matched)}")
    (DATA / "matched.jsonl").write_text("\n".join(json.dumps(j) for j in matched))

    # Split by source: LinkedIn Easy Apply vs external ATS
    li_jobs  = [j for j in matched if j.get("source","").startswith(("linkedin","jobspy:linkedin"))]
    ats_jobs = [j for j in matched if j not in li_jobs]

    results = li_apply(li_jobs, cfg) + ats_apply(ats_jobs, cfg)

    def _c(key_pred):
        return sum(1 for r in results if key_pred(r.get("result","")))

    submitted = _c(lambda r: r == "submitted")
    dry       = _c(lambda r: r.startswith("dry_run"))
    skipped   = _c(lambda r: r.startswith("skipped_"))
    errored   = _c(lambda r: r.startswith(("error:", "nav_error", "no_submit", "no_answer", "no_easy_apply")))
    print(f"[run] submitted={submitted} dry={dry} skipped={skipped} errored={errored} total={len(results)}")

if __name__ == "__main__":
    main()
