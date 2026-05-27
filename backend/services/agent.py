"""
Orchestrator — coordinates the three agents.

Flow for job-application requests:
  Search Agent  →  Extract Agent  →  (doc_service handles Doc Agent)

Flow for all other requests:
  Generic tool-calling loop (search + fetch + extract in one conversation).
"""

import json
import re
from typing import Any

from openai import AsyncOpenAI

from config import settings
from services.gmail_service import GmailService
from agents import search_agent, extract_agent


# ─── Generic tool-calling path (non-job requests) ────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": (
                "Search Gmail using Gmail query syntax "
                "(from:, subject:, after:YYYY/MM/DD, etc.). "
                "Returns email IDs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 50},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_email_details",
            "description": "Fetch subject, sender, date and body for up to 20 emails.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                },
                "required": ["email_ids"],
            },
        },
    },
]

_GENERIC_SYSTEM = """You are a personal Gmail assistant. Search Gmail and extract data \
into a structured JSON document.

RULES:
- READ-ONLY. Never send, delete, or modify emails.
- Use 2-4 search query variations. Fetch details in batches of 20.
- Return ONLY valid JSON — no markdown, no explanation.

OUTPUT FORMAT:
{
  "summary": "Brief description of what was found",
  "data": [{"field1": "value1", ...}, ...],
  "column_order": ["field1", ...],
  "output_format": "excel" or "word"
}"""

_CONTEXT_CHAR_BUDGET = 100_000


def _safe_len(m: Any) -> int:
    try:
        return len(json.dumps(m))
    except TypeError:
        return len(str(m))


def _trim_messages(messages: list[dict]) -> list[dict]:
    if sum(_safe_len(m) for m in messages) <= _CONTEXT_CHAR_BUDGET:
        return messages
    trimmed = []
    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        if role == "system" or (role == "user" and i <= 1):
            trimmed.append(msg)
        elif role == "tool" and len(msg.get("content", "")) > 500:
            trimmed.append({**msg, "content": msg["content"][:300] + "... [trimmed]"})
        else:
            trimmed.append(msg)
    return trimmed


# ─── Orchestrator ─────────────────────────────────────────────────────────────


class GmailAgent:

    def __init__(self, gmail_service: GmailService):
        self._gmail = gmail_service
        self._openai = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, user_request: str, doc_structure: dict) -> dict[str, Any]:
        """
        Route to the right pipeline based on request type.
        """
        if search_agent.is_job_request(user_request):
            print("[orchestrator] -> job-application pipeline")
            return await self._run_job_pipeline(user_request, doc_structure)
        else:
            print("[orchestrator] -> generic tool-calling pipeline")
            return await self._run_generic(user_request, doc_structure)

    # ── Job-application pipeline ──────────────────────────────────────────────

    async def _run_job_pipeline(
        self, user_request: str, doc_structure: dict
    ) -> dict[str, Any]:
        # ── Agent 1: Search ───────────────────────────────────────────────────
        after_date = search_agent.extract_after_date(user_request)
        print(f"[orchestrator] searching emails after {after_date}")
        emails = search_agent.run(self._gmail, after_date)

        if not emails:
            return {
                "summary": f"No job application emails found after {after_date}.",
                "data": [],
                "column_order": [
                    "date_of_application", "method_of_application", "company",
                    "position", "expense", "interview_offer_of_employment",
                    "accepted_rejected_reason",
                ],
                "output_format": "word",
            }

        # ── Agent 2: Extract ──────────────────────────────────────────────────
        print(f"[orchestrator] search found {len(emails)} emails -> sending to extract agent")
        records = await extract_agent.run(emails)
        print(f"[orchestrator] extract returned {len(records)} records (dropped {len(emails) - len(records)})")

        doc_type = doc_structure.get("type", "excel")
        return {
            "summary": (
                f"Found {len(records)} job application confirmations after {after_date}."
            ),
            "data": records,
            "column_order": [
                "date_of_application", "method_of_application", "company",
                "position", "expense", "interview_offer_of_employment",
                "accepted_rejected_reason",
            ],
            "output_format": "word" if "word" in doc_type else "excel",
        }

    # ── Generic tool-calling pipeline ────────────────────────────────────────

    async def _run_generic(
        self, user_request: str, doc_structure: dict
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": _GENERIC_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Document structure:\n{json.dumps(doc_structure, indent=2)}\n\n"
                    f"User request:\n{user_request}\n\n"
                    "Search Gmail and extract the requested data."
                ),
            },
        ]

        max_iterations = 20
        for iteration in range(max_iterations):
            messages = _trim_messages(messages)

            if iteration == max_iterations - 2:
                messages.append({
                    "role": "user",
                    "content": "Stop searching now. Return the final JSON with all data collected.",
                })

            response = await self._openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="none" if iteration == max_iterations - 1 else "auto",
                temperature=0.1,
                max_tokens=16000,
            )

            message = response.choices[0].message

            if message.tool_calls:
                messages.append(message.model_dump(exclude_none=True))
                for tc in message.tool_calls:
                    result = await self._execute_tool(tc)
                    result_str = json.dumps(result)
                    if len(result_str) > 20000:
                        result_str = result_str[:20000] + "... [truncated]"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })
            else:
                raw = (message.content or "").strip()
                raw = re.sub(r"^```[a-z]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw).strip()
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"Agent returned non-JSON: {raw[:300]}") from exc

        raise RuntimeError("Agent exceeded maximum iterations.")

    async def _execute_tool(self, tool_call) -> Any:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        try:
            if name == "search_emails":
                return self._gmail.search_emails(
                    query=args["query"],
                    max_results=min(args.get("max_results", 50), 100),
                )
            elif name == "get_email_details":
                return self._gmail.get_emails(args["email_ids"])
            else:
                return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            err = str(e)
            if any(k in err.lower() for k in ("token expired", "invalid credentials", "invalid_grant", "401")):
                raise
            return {"error": f"Tool '{name}' failed: {err}", "skipped": True}
