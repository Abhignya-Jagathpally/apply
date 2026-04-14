"""Unified job scraper backed by JobSpy.

Replaces the custom LinkedIn Playwright scraper + ATS API scrapers. JobSpy
queries LinkedIn, Indeed, Glassdoor, ZipRecruiter, and Google in parallel
and returns a normalized DataFrame.

Docs: https://github.com/cullenwatson/JobSpy
"""
from __future__ import annotations
from typing import Iterable
import pandas as pd
from jobspy import scrape_jobs

SITES = ["linkedin", "indeed", "glassdoor", "zip_recruiter", "google"]


def _one(location: str, search_term: str, is_remote: bool, hours_old: int) -> pd.DataFrame:
    try:
        return scrape_jobs(
            site_name=SITES,
            search_term=search_term,
            google_search_term=f"{search_term} jobs {location}",
            location=location,
            results_wanted=50,
            hours_old=hours_old,
            country_indeed="USA",
            is_remote=is_remote,
            linkedin_fetch_description=True,  # needed for keyword matching later
        )
    except Exception as e:
        print(f"[jobspy] {search_term} @ {location} failed: {e}")
        return pd.DataFrame()


def fetch(cfg: dict) -> list[dict]:
    terms = cfg.get("search_terms", [
        "data science intern", "machine learning intern", "ai intern",
        "data engineer intern", "research intern", "analytics intern",
    ])
    frames: list[pd.DataFrame] = []
    for t in terms:
        frames.append(_one("Dallas, TX", t, False, 72))
        frames.append(_one("USA",        t, True,  72))
    if not frames:
        return []
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["job_url"])
    jobs: list[dict] = []
    for _, r in df.iterrows():
        jobs.append({
            "source":   f"jobspy:{r.get('site','?')}",
            "job_id":   f"{r.get('site','js')}:{r.get('id') or r.get('job_url')}",
            "title":    r.get("title", "") or "",
            "company":  r.get("company", "") or "",
            "location": r.get("location", "") or "",
            "remote":   bool(r.get("is_remote", False)),
            "url":      r.get("job_url", ""),
            "description": (r.get("description") or "")[:6000],  # truncate
            "easy_apply":  bool(r.get("linkedin_easy_apply", False)) if r.get("site") == "linkedin" else False,
        })
    return jobs
