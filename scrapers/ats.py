"""Public ATS board scrapers. All unauthenticated JSON APIs."""
from __future__ import annotations
import requests

GH = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
LV = "https://api.lever.co/v0/postings/{slug}?mode=json"
AS = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
WK = "https://apply.workable.com/api/v3/accounts/{slug}/jobs"
SR = "https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100"
BZ = "https://api.breezy.hr/v3/company/{slug}/positions?state=published"


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
                "company": slug, "location": loc,
                "remote": "remote" in (loc+commitment).lower(),
                "url": j.get("hostedUrl"),
                "description": (j.get("descriptionPlain") or "")[:5000],
                "easy_apply": False,
            })
        return out
    except Exception as e:
        print(f"[lever:{slug}] {e}"); return []


def ashby(slug: str) -> list[dict]:
    try:
        r = requests.get(AS.format(slug=slug), timeout=15); r.raise_for_status()
        out = []
        for j in r.json().get("jobs", []):
            loc = j.get("locationName","") or ""
            out.append({
                "source": f"ashby:{slug}",
                "job_id": f"ashby:{slug}:{j.get('id')}",
                "title": j.get("title",""), "company": slug, "location": loc,
                "remote": bool(j.get("isRemote")),
                "url": j.get("jobUrl") or j.get("applyUrl"),
                "description": (j.get("descriptionPlain") or "")[:5000],
                "easy_apply": False,
            })
        return out
    except Exception as e:
        print(f"[ashby:{slug}] {e}"); return []


def workable(slug: str) -> list[dict]:
    try:
        r = requests.get(WK.format(slug=slug), timeout=15); r.raise_for_status()
        out = []
        for j in r.json().get("results", []):
            loc = ", ".join(filter(None, [j.get("location",{}).get("city",""),
                                          j.get("location",{}).get("country","")]))
            out.append({
                "source": f"workable:{slug}",
                "job_id": f"wk:{slug}:{j.get('shortcode')}",
                "title": j.get("title",""), "company": slug, "location": loc,
                "remote": bool(j.get("remote")),
                "url": j.get("url") or f"https://apply.workable.com/{slug}/j/{j.get('shortcode')}/",
                "description": (j.get("description") or "")[:5000],
                "easy_apply": False,
            })
        return out
    except Exception as e:
        print(f"[workable:{slug}] {e}"); return []


def smartrecruiters(slug: str) -> list[dict]:
    try:
        r = requests.get(SR.format(slug=slug), timeout=15); r.raise_for_status()
        out = []
        for j in r.json().get("content", []):
            loc_d = j.get("location",{}) or {}
            loc = ", ".join(filter(None, [loc_d.get("city",""), loc_d.get("country","")]))
            out.append({
                "source": f"smartrecruiters:{slug}",
                "job_id": f"sr:{slug}:{j.get('id')}",
                "title": j.get("name",""), "company": slug, "location": loc,
                "remote": bool(loc_d.get("remote")),
                "url": j.get("applyUrl") or j.get("ref"),
                "description": "", "easy_apply": False,
            })
        return out
    except Exception as e:
        print(f"[smartrecruiters:{slug}] {e}"); return []


def breezy(slug: str) -> list[dict]:
    try:
        r = requests.get(BZ.format(slug=slug), timeout=15); r.raise_for_status()
        out = []
        for j in r.json():
            loc_d = j.get("location",{}) or {}
            loc = ", ".join(filter(None, [loc_d.get("name",""), loc_d.get("country","")]))
            out.append({
                "source": f"breezy:{slug}",
                "job_id": f"bz:{slug}:{j.get('_id')}",
                "title": j.get("name",""), "company": slug, "location": loc,
                "remote": bool(loc_d.get("is_remote")),
                "url": j.get("url") or f"https://{slug}.breezy.hr/p/{j.get('_id')}",
                "description": (j.get("description") or "")[:5000],
                "easy_apply": False,
            })
        return out
    except Exception as e:
        print(f"[breezy:{slug}] {e}"); return []
