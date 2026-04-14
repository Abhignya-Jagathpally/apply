"""Smart filtering: domain+role keywords, location, seniority, negatives, dedup."""
from __future__ import annotations
import json, re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _any(haystack: str, needles: list[str]) -> bool:
    h = haystack.lower()
    return any(n.lower() in h for n in needles)


def matches_title(title: str, cfg: dict) -> bool:
    t = title.lower()
    if _any(t, cfg["title_negative"]):
        return False
    # Must be an intern/early-career role
    if not _any(t, cfg["title_positive_role"]):
        return False
    # Accept if it's explicitly a data/AI domain title...
    if _any(t, cfg["title_positive_domain"]):
        return True
    # ...OR if it's a generic tech intern title the owner would also consider.
    # This is the "smart" relaxation: once location+role is matched, a generic
    # SWE/Research intern at a tech-heavy employer is in scope.
    generic_ok = ["software", "engineer", "engineering", "research",
                  "quant", "applied", "platform", "backend"]
    return _any(t, generic_ok)


def matches_location(location: str, remote: bool, cfg: dict) -> bool:
    if remote:
        # Remote-USA only (exclude international-remote)
        loc = location.lower()
        if any(x in loc for x in ["united states", "usa", "remote"]) and \
           not any(x in loc for x in ["canada", "india", "uk", "emea", "europe"]):
            return True
    return _any(location, cfg["dallas_area"])


def resume_variant(title: str) -> str:
    t = title.lower()
    if re.search(r"\b(research|scientist|phd|ph\.d)\b", t): return "DS_ML_Research"
    if re.search(r"\b(ml|machine learning|deep learning|nlp|computer vision|ai)\b", t):
        return "AI_Engineering" if "engineer" in t else "DS_ML_Research"
    if re.search(r"\bdata engineer", t): return "Data_Engineering"
    if re.search(r"\banalyst|analytics", t): return "Data_Analytics"
    return "DS_ML_Research"


def load_applied() -> set[str]:
    p = DATA_DIR / "applied.jsonl"
    if not p.exists(): return set()
    ids = set()
    for line in p.read_text().splitlines():
        try: ids.add(json.loads(line)["job_id"])
        except Exception: pass
    return ids


def filter_jobs(jobs: list[dict], cfg: dict) -> list[dict]:
    applied = load_applied()
    seen: set[str] = set()
    out = []
    for j in jobs:
        jid = j.get("job_id") or f"{j.get('source')}:{j.get('url')}"
        if jid in applied or jid in seen: continue
        if not matches_title(j.get("title",""), cfg): continue
        if not matches_location(j.get("location",""), j.get("remote", False), cfg): continue
        j["job_id"] = jid
        j["resume_variant"] = resume_variant(j["title"])
        seen.add(jid)
        out.append(j)
    return out
