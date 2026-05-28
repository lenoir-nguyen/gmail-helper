"""
Agent 2 - Extract Agent

Responsibility: given a batch of raw email dicts, call the LLM once and
return a list of structured job-application records.

No Gmail tools - pure LLM inference on the email content already provided.
Processes emails in batches of 25 to keep each LLM call small and focused.
"""

import json
import re

from openai import AsyncOpenAI
from config import settings


_SYSTEM_PROMPT = """You extract job application data from emails.

IMPORTANT: Extract a record for EVERY email in the list. Do NOT skip any email.
These emails were already pre-filtered to be job application related.

For each email extract:

  date_of_application           : the email's "date" field, formatted YYYY-MM-DD
  company                       : the hiring company name.
                                  - Read it from the subject line or email body.
                                  - If sender is an ATS (Workday, Greenhouse, Lever,
                                    Taleo, iCIMS, BambooHR, SmartRecruiters, Jobvite),
                                    find the real company name in the body text.
                                  - If still unclear, extract the company name from
                                    the sender's email domain (e.g. rbc.com -> "RBC").
  position                      : the job title from subject or body.
                                  If not explicitly stated, write "Not specified".
  method_of_application         : one of:
      "LinkedIn"        - sender contains linkedin.com OR subject/body mentions LinkedIn
      "Indeed"          - sender contains indeed.com OR subject/body mentions Indeed
      "Company Website" - ATS sender domain OR no clear platform signal
      "Referral"        - body explicitly mentions a referral
  expense                       : always ""
  interview_offer_of_employment : always ""
  accepted_rejected_reason      : read the email body carefully and classify as
                                  exactly one of these four values:

      "no response" - The email is a standard application acknowledgement.
                      Signals: "thank you for applying", "we received your application",
                      "we will review", "we'll be in touch", "under review",
                      "we will contact you", "application submitted successfully".
                      This is the default when no stronger signal is present.

      "rejected"    - The email explicitly says they are NOT moving forward.
                      Signals: "not moving forward", "we will not be proceeding",
                      "regret to inform", "unfortunately", "we have decided",
                      "position has been filled", "other candidates",
                      "we won't be moving forward", "no longer under consideration",
                      "we have moved forward with other applicants".

      "interviewed" - The email invites the candidate to an interview or next step.
                      Signals: "we would like to invite you", "schedule an interview",
                      "phone screen", "video interview", "please select a time",
                      "next steps", "speak with our team", "meet with us",
                      "we'd like to learn more about you", "schedule a call".

      "accepted"    - The email contains a job offer or acceptance.
                      Signals: "offer of employment", "we are pleased to offer",
                      "congratulations", "welcome to the team", "job offer",
                      "offer letter", "pleased to extend an offer".

Return a JSON array with exactly one entry per email - no markdown, no skipping.
accepted_rejected_reason must be one of: "no response", "rejected", "interviewed", "accepted".

[
  {
    "date_of_application": "2026-04-15",
    "company": "Acme Corp",
    "position": "Senior Software Engineer",
    "method_of_application": "LinkedIn",
    "expense": "",
    "interview_offer_of_employment": "",
    "accepted_rejected_reason": "no response"
  }
]
"""


async def run_batch(emails: list[dict], client: AsyncOpenAI) -> list[dict]:
    """Extract structured records from one batch of emails."""
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Extract job application data from these {len(emails)} emails:\n\n"
                    # ensure_ascii=True escapes all non-ASCII chars to \uXXXX
                    # so Windows charmap never sees raw Unicode in the payload
                    + json.dumps(emails, ensure_ascii=True)
                ),
            },
        ],
        temperature=0.0,
        max_tokens=8000,
    )

    raw = (response.choices[0].message.content or "[]").strip()

    # Strip accidental markdown fences
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw).strip()

    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        print(f"[extract_agent] JSON parse failed for batch. Raw: {raw[:300]}")
        return []


async def run(emails: list[dict]) -> list[dict]:
    """
    Process all emails in batches of 25.
    Returns sorted list of job application records.
    """
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    all_data: list[dict] = []
    batch_size = 25

    for i in range(0, len(emails), batch_size):
        batch = emails[i : i + batch_size]
        batch_num = i // batch_size + 1
        print(f"[extract_agent] processing batch {batch_num} ({len(batch)} emails)...")

        records = await run_batch(batch, client)
        all_data.extend(records)
        print(f"[extract_agent] batch {batch_num}: extracted {len(records)} records")

    # Sort by date ascending
    all_data.sort(key=lambda r: r.get("date_of_application", ""))

    print(f"[extract_agent] total records extracted: {len(all_data)}")
    return all_data
