"""Main pipeline entrypoint. Run daily.

  python run.py
"""
from __future__ import annotations
import json, yaml
from pathlib import Path
from scrapers.linkedin import fetch_jobs as li_fetch
from scrapers.ats import greenhouse, lever
from filters.smart import filter_jobs
from apply.linkedin_easy_apply import run as li_apply

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"; DATA.mkdir(exist_ok=True)

def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())

    all_urls = cfg["linkedin_saved_searches"] + cfg["linkedin_canonical_searches"]
    jobs: list[dict] = []
    jobs += li_fetch(all_urls)
    for slug in cfg["greenhouse_slugs"]: jobs += greenhouse(slug)
    for slug in cfg["lever_slugs"]:      jobs += lever(slug)

    print(f"[run] raw jobs: {len(jobs)}")
    # show a sample so we can sanity-check what the scrapers brought in
    for j in jobs[:20]:
        print(f"  [sample] {j.get('source','?'):22} | {j.get('location','')[:40]:40} | {j.get('title','')[:80]}")
    (DATA / "jobs.jsonl").write_text("\n".join(json.dumps(j) for j in jobs))

    matched = filter_jobs(jobs, cfg)
    print(f"[run] after filter: {len(matched)}")
    (DATA / "matched.jsonl").write_text("\n".join(json.dumps(j) for j in matched))

    results = li_apply(matched, cfg)
    submitted = sum(1 for r in results if r.get("result") == "submitted")
    dry       = sum(1 for r in results if r.get("result","").startswith("dry_run"))
    manual    = sum(1 for r in results if r.get("result") == "non_easy_apply_needs_manual")
    print(f"[run] submitted={submitted} dry={dry} manual={manual} total={len(results)}")

if __name__ == "__main__":
    main()
