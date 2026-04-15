"""Custom scrapers for boards JobSpy doesn't cover.

Each function returns a list of normalized job dicts:
  {source, job_id, title, company, location, remote, url, description, easy_apply}
"""
from __future__ import annotations
import re, requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
TERMS = ["data science intern", "machine learning intern", "ai intern",
         "data engineer intern", "research intern"]
LOCS = [("Dallas, TX", False), ("United States", True)]


def dice() -> list[dict]:
    out, seen = [], set()
    for t in TERMS:
        for loc, _ in LOCS:
            try:
                r = requests.get(
                    "https://marketplace-api.dice.com/api/v1/jobs/search",
                    params={"q": t, "location": loc, "pageSize": 50, "page": 1,
                            "filters.jobType": "INTERN"},
                    headers=UA, timeout=15)
                r.raise_for_status()
                for j in r.json().get("data", []):
                    jid = f"dice:{j.get('id') or j.get('guid')}"
                    if jid in seen: continue
                    seen.add(jid)
                    out.append({
                        "source":"dice","job_id":jid,
                        "title": j.get("title",""),
                        "company": j.get("company",""),
                        "location": j.get("jobLocation",{}).get("displayName",""),
                        "remote": bool(j.get("isRemote")),
                        "url": j.get("detailsPageUrl",""),
                        "description": j.get("summary","") or "",
                        "easy_apply": False,
                    })
            except Exception as e:
                print(f"[dice:{t}@{loc}] {e}")
    return out


def simplyhired() -> list[dict]:
    out, seen = [], set()
    for t in TERMS:
        for loc, _ in LOCS:
            try:
                r = requests.get("https://www.simplyhired.com/search",
                                 params={"q": t, "l": loc}, headers=UA, timeout=15)
                if r.status_code != 200: continue
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.select("a[data-mdref='serp-jobcard-link'], a.SerpJob-link"):
                    url = a.get("href","")
                    if url.startswith("/"): url = "https://www.simplyhired.com" + url
                    title = a.get_text(strip=True)
                    jid = f"simplyhired:{url}"
                    if not title or jid in seen: continue
                    seen.add(jid)
                    out.append({
                        "source":"simplyhired","job_id":jid,
                        "title": title, "company": "", "location": loc,
                        "remote": "remote" in loc.lower(),
                        "url": url, "description": "", "easy_apply": False,
                    })
            except Exception as e:
                print(f"[simplyhired:{t}@{loc}] {e}")
    return out


def ycombinator() -> list[dict]:
    """Work at a Startup public job feed."""
    out = []
    try:
        r = requests.get("https://www.workatastartup.com/api/jobs/search",
                         params={"query":"data intern","remote":"true"},
                         headers=UA, timeout=15)
        if r.status_code != 200: return []
        for j in r.json().get("results", []):
            jid = f"yc:{j.get('id')}"
            out.append({
                "source":"yc","job_id":jid,
                "title": j.get("title",""), "company": j.get("company_name",""),
                "location": j.get("location","") or "Remote",
                "remote": bool(j.get("remote")),
                "url": f"https://www.workatastartup.com/jobs/{j.get('id')}",
                "description": j.get("description","")[:5000],
                "easy_apply": False,
            })
    except Exception as e:
        print(f"[yc] {e}")
    return out


def zintellect() -> list[dict]:
    """ORAU/DOE internship catalog."""
    out = []
    try:
        r = requests.get("https://www.zintellect.com/Catalog/Opportunities",
                         params={"keyword":"data"}, headers=UA, timeout=20)
        if r.status_code != 200: return []
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("div.opportunity-card, a.opportunity-link"):
            title = card.get_text(" ", strip=True)[:140]
            href = card.get("href","") if card.name == "a" else ""
            if href and href.startswith("/"): href = "https://www.zintellect.com" + href
            if not title or not href: continue
            out.append({
                "source":"zintellect","job_id":f"zintellect:{href}",
                "title": title, "company":"DOE/ORAU",
                "location":"Various (US)","remote": False,
                "url": href, "description":"", "easy_apply": False,
            })
    except Exception as e:
        print(f"[zintellect] {e}")
    return out


def fetch_all() -> list[dict]:
    # dice skipped: marketplace-api.dice.com is DNS-unreachable from GH Actions
    jobs = []
    for fn in (simplyhired, ycombinator, zintellect):
        try: jobs += fn()
        except Exception as e: print(f"[custom_boards:{fn.__name__}] {e}")
    return jobs
