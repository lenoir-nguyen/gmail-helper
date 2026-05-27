"""
Agent 1 — Search Agent

Responsibility: find ALL relevant email IDs via multiple Gmail queries,
deduplicate them, then fetch full email details in batches.

No LLM involved — pure Python + Gmail API.
Returns a list of email dicts ready for the Extract Agent.
"""

import re
from services.gmail_service import GmailService


_MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}

# Phrases that indicate a job application confirmation email
_JOB_KEYWORDS = [
    "job application", "job applications", "applying", "applied",
    "application confirmation", "mitigation tracker", "job search",
]


def is_job_request(text: str) -> bool:
    """Detect whether the user request is about job applications."""
    t = text.lower()
    return any(k in t for k in _JOB_KEYWORDS)


def extract_after_date(text: str) -> str:
    """Parse a date from the request and return it as YYYY/MM/DD."""
    t = text.lower()
    # "April 1, 2026" or "April 1 2026"
    m = re.search(
        r"(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})",
        t,
    )
    if m:
        return f"{m.group(3)}/{_MONTH_MAP[m.group(1)]}/{m.group(2).zfill(2)}"
    # ISO / numeric: "2026-04-01" or "2026/04/01"
    m = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", text)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return "2026/01/01"


# ── Job application queries ───────────────────────────────────────────────────

def _build_job_queries(after_date: str) -> list[str]:
    return [
        # Core "thank you" confirmation patterns
        f'"thank you for applying" after:{after_date}',
        f'"thanks for applying" after:{after_date}',
        f'"thank you for your application" after:{after_date}',
        f'"thanks for your application" after:{after_date}',
        f'"thank you for submitting your application" after:{after_date}',
        f'"thank you for your recent application" after:{after_date}',

        # "Received" confirmation patterns
        f'"we received your application" after:{after_date}',
        f'"we\'ve received your application" after:{after_date}',
        f'"your application has been received" after:{after_date}',
        f'"your application was received" after:{after_date}',
        f'"application successfully submitted" after:{after_date}',
        f'"successfully submitted your application" after:{after_date}',

        # Interest / review patterns
        f'"thank you for your interest" (position OR role OR engineer OR developer OR analyst OR consultant OR designer OR manager) after:{after_date}',

        # Subject-line patterns (catches ATS emails that vary body wording)
        f'subject:application subject:("thank you" OR received OR confirmation OR submitted) after:{after_date}',
        f'subject:applying after:{after_date}',
        f'subject:"your application" after:{after_date}',
        f'subject:"application received" after:{after_date}',
        f'subject:"application submitted" after:{after_date}',
        f'subject:"application confirmation" after:{after_date}',
    ]


# ── Public API ────────────────────────────────────────────────────────────────

def run(gmail: GmailService, after_date: str) -> list[dict]:
    """
    Run all job-application queries, deduplicate IDs, fetch details.
    Returns a flat list of email dicts: {id, subject, from, date, body}.
    """
    queries = _build_job_queries(after_date)
    seen: set[str] = set()
    all_ids: list[str] = []

    for q in queries:
        try:
            results = gmail.search_emails(q)  # paginated, no cap — gets ALL matches
            new_ids = [r["id"] for r in results if r["id"] not in seen]
            seen.update(new_ids)
            all_ids.extend(new_ids)
            print(f"[search_agent] '{q[:65]}' -> {len(results)} hits, {len(new_ids)} new")
        except Exception as e:
            print(f"[search_agent] query failed: {e}")

    print(f"[search_agent] total unique email IDs: {len(all_ids)}")

    # Fetch email details in batches of 20
    emails: list[dict] = []
    batch_size = 20
    for i in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[i : i + batch_size]
        batch = gmail.get_emails(batch_ids)
        # Filter out error responses
        valid = [e for e in batch if "error" not in e]
        emails.extend(valid)
        print(f"[search_agent] fetched {len(valid)}/{len(batch_ids)} emails (batch {i // batch_size + 1})")

    print(f"[search_agent] total emails ready for extraction: {len(emails)}")
    return emails
