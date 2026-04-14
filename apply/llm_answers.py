"""LLM-based answerer for LinkedIn Easy Apply screening questions.

Pattern inspired by feder-cr/Auto_Jobs_Applier_AIHawk (NOT copied — GPL).
The system prompt enforces:
  * answers must be grounded in the resume + fact sheet
  * NEVER emit a GitHub, portfolio, or personal website URL
  * numeric questions -> integer-only
  * years-of-experience questions -> honest integer from fact sheet

Uses Anthropic Claude via the Messages API. Set ANTHROPIC_API_KEY.
"""
from __future__ import annotations
import os, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS_FILE = ROOT / "resume" / "facts.yaml"

SYSTEM = """You are filling out a single field on a job application form for
Abhignya Jagathpally. Use only the provided facts; if a fact is missing,
answer "N/A" for text or "0" for numbers. NEVER include a GitHub URL, a
portfolio URL, or any personal website. Keep answers short (<= 280 chars
unless the question explicitly requests a paragraph). For yes/no questions
answer exactly "Yes" or "No". For numeric questions answer an integer only.
Return ONLY the answer text with no preamble, no quotes, no markdown."""


def _facts() -> str:
    if FACTS_FILE.exists():
        return FACTS_FILE.read_text()
    # Minimal fallback if facts.yaml is missing
    return """name: Abhignya Jagathpally
email: abhignya.j@gmail.com
education: PhD student, Computer Science / Data Science, University of North Texas
years_experience_total: 3
years_experience_python: 3
years_experience_sql: 3
years_experience_pyspark: 3
years_experience_ml: 2
authorized_to_work_us: Yes
require_sponsorship: Yes
willing_to_relocate: Yes
"""


def answer(question: str, options: list[str] | None = None) -> str:
    try:
        from anthropic import Anthropic
    except ImportError:
        return ""  # library not installed -> caller will skip
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return ""
    client = Anthropic()
    prompt = f"FACTS:\n{_facts()}\n\nQUESTION: {question}"
    if options:
        prompt += f"\nOPTIONS: {json.dumps(options)}\nReturn exactly one option verbatim."
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # Hard safety: strip any URL the model emitted anyway
    text = re.sub(r"https?://\S+", "", text).strip()
    return text
