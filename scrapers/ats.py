"""Public ATS board scrapers (Greenhouse + Lever). Unauthenticated JSON APIs."""
from __future__ import annotations
import requests

GH = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
LV = "https://api.lever.co/v0/postings/{slug}?mode=json"


def greenhouse(slug: str) -> list[dict]:
    try:
        r = requests.get(GH.format(slug=slug), timeout=15); r.raise_for_status()
        out = []
        for j in r.json().get("jobs", []):
            loc = (j.get("location") or {}).get("name", "") or ""
            out.append({
                "source": f"greenhouse:{slug}",
                "job_id": f"gh:{slug}:{j['id']}",
                "title": j.get("title",""),
                "company": slug,
                "location": loc,
                "remote": "remote" in loc.lower(),
                "url": j.get("absolute_url"),
                "easy_apply": False,
            })
        return out
    except Exception as e:
        print(f"[greenhouse:{slug}] {e}"); return []


def lever(slug: str) -> list[dict]:
    try:
        r = requests.get(LV.format(slug=slug), timeout=15); r.raise_for_status()
        out = []
        for j in r.json():
            cats = j.get("categories", {}) or {}
            loc = cats.get("location","") or ""
            commitment = cats.get("commitment","") or ""
            out.append({
                "source": f"lever:{slug}",
                "job_id": f"lv:{slug}:{j['id']}",
                "title": f"{j.get('text','')} {('('+commitment+')') if commitment else ''}".strip(),
                "company": slug,
                "location": loc,
                "remote": "remote" in (loc+commitment).lower(),
                "url": j.get("hostedUrl"),
                "easy_apply": False,
            })
        return out
    except Exception as e:
        print(f"[lever:{slug}] {e}"); return []
