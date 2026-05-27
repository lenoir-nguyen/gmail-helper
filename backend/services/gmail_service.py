"""
Gmail API service — READ ONLY.

Wraps the Gmail API with only search/read operations.
No write, send, delete, label, or modify operations exist here.
"""

import base64
import email as email_lib
from io import BytesIO
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pdfminer.high_level import extract_text as pdf_extract_text


def _build_gmail(access_token: str):
    """Build a Gmail API client from an existing access token."""
    creds = Credentials(token=access_token)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _decode_body(part: dict) -> str:
    """Decode a base64url-encoded email body part to a string."""
    data = part.get("body", {}).get("data", "")
    if not data:
        return ""
    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")


def _extract_parts(payload: dict) -> dict[str, str]:
    """
    Recursively walk a message payload and collect text/plain and text/html parts.
    Returns {"plain": "...", "html": "..."}.
    """
    result = {"plain": "", "html": ""}
    mime = payload.get("mimeType", "")

    if mime == "text/plain":
        result["plain"] = _decode_body(payload)
    elif mime == "text/html":
        result["html"] = _decode_body(payload)
    elif "parts" in payload:
        for part in payload["parts"]:
            sub = _extract_parts(part)
            result["plain"] += sub["plain"]
            result["html"] += sub["html"]

    return result


def _get_header(headers: list[dict], name: str) -> str:
    """Extract a specific header value by name (case-insensitive)."""
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _list_attachments(payload: dict, parent_id: str = "") -> list[dict]:
    """
    Recursively collect attachment metadata from a message payload.
    Returns a list of {"filename": ..., "mime_type": ..., "attachment_id": ..., "size": ...}.
    """
    attachments = []
    if "parts" not in payload:
        return attachments

    for part in payload["parts"]:
        body = part.get("body", {})
        if body.get("attachmentId"):
            attachments.append(
                {
                    "filename": part.get("filename", ""),
                    "mime_type": part.get("mimeType", ""),
                    "attachment_id": body["attachmentId"],
                    "size": body.get("size", 0),
                }
            )
        # Recurse into nested parts
        if "parts" in part:
            attachments.extend(_list_attachments(part))

    return attachments


# ─── Public API ───────────────────────────────────────────────────────────────


class GmailService:
    """Read-only Gmail operations."""

    def __init__(self, access_token: str):
        self._token = access_token
        self._service = _build_gmail(access_token)

    # ── search ────────────────────────────────────────────────────────────────

    def search_emails(self, query: str, max_results: int = 500) -> list[dict]:
        """
        Search Gmail and return ALL matching email IDs, following pagination.

        Gmail's messages.list returns at most 500 per page and provides a
        nextPageToken when more results exist.  Without following that token
        we silently miss everything beyond the first page.

        max_results caps the total across all pages (default 500, hard cap 2000).
        """
        cap = min(max_results, 2000)
        all_messages: list[dict] = []
        page_token: str | None = None

        try:
            while len(all_messages) < cap:
                fetch = min(500, cap - len(all_messages))   # max 500 per API call
                kwargs: dict = {"userId": "me", "q": query, "maxResults": fetch}
                if page_token:
                    kwargs["pageToken"] = page_token

                result = self._service.users().messages().list(**kwargs).execute()
                page = result.get("messages", [])
                all_messages.extend(page)

                page_token = result.get("nextPageToken")
                if not page_token or not page:
                    break   # no more pages

        except Exception as e:
            err = str(e)
            if "401" in err or "invalid_grant" in err or "Invalid Credentials" in err:
                raise RuntimeError(
                    "Gmail token expired or invalid. Please disconnect and reconnect your Gmail account."
                ) from e
            raise

        return [{"id": m["id"], "thread_id": m["threadId"]} for m in all_messages]

    # ── fetch single email ─────────────────────────────────────────────────────

    def get_email(self, message_id: str) -> dict[str, Any]:
        """
        Fetch subject, sender, date and body of a single email.
        Only subject + body are needed for data extraction — no attachments, no snippet.
        Gracefully handles 404s (deleted/archived emails).
        """
        try:
            msg = (
                self._service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except Exception as e:
            return {"id": message_id, "error": f"Email not accessible: {str(e)}"}

        headers = msg.get("payload", {}).get("headers", [])
        body_parts = _extract_parts(msg.get("payload", {}))

        # Prefer plain text; fall back to a note about HTML
        body_text = body_parts["plain"] or (
            "[HTML body — plain text unavailable]" if body_parts["html"] else ""
        )

        return {
            "id": msg["id"],
            "subject": _get_header(headers, "Subject"),
            "from": _get_header(headers, "From"),
            "date": _get_header(headers, "Date"),
            "body": body_text[:300],  # subject line already has company+position; 300 chars covers the confirmation sentence
        }

    def get_emails(self, message_ids: list[str]) -> list[dict]:
        """Fetch multiple emails by ID."""
        return [self.get_email(mid) for mid in message_ids]

    # ── fetch thread ──────────────────────────────────────────────────────────

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        """
        Fetch a full email thread (all messages in the conversation).
        Returns thread_id and a list of messages.
        Gracefully handles 404s (deleted/archived threads).
        """
        try:
            thread = (
                self._service.users()
                .threads()
                .get(userId="me", id=thread_id, format="full")
                .execute()
            )
        except Exception as e:
            # Thread may have been deleted, archived, or moved — skip gracefully
            return {
                "thread_id": thread_id,
                "messages": [],
                "error": f"Thread not accessible: {str(e)}",
            }

        messages = []
        for msg in thread.get("messages", []):
            headers = msg.get("payload", {}).get("headers", [])
            body_parts = _extract_parts(msg.get("payload", {}))
            messages.append(
                {
                    "id": msg["id"],
                    "from": _get_header(headers, "From"),
                    "date": _get_header(headers, "Date"),
                    "body": body_parts["plain"][:1500],
                }
            )

        return {"thread_id": thread_id, "messages": messages}

    # ── attachments ───────────────────────────────────────────────────────────

    def get_attachment_text(self, message_id: str, attachment_id: str) -> str:
        """
        Download an attachment and extract its text content.
        Supports PDF files; returns raw bytes for others.
        Returns extracted text string (max 5000 chars).
        """
        # Guard against empty or invalid attachment IDs — avoids malformed API URLs
        if not attachment_id or not attachment_id.strip():
            return "[Invalid attachment ID — skipped]"

        try:
            attachment = (
                self._service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
        except Exception as e:
            return f"[Attachment not accessible: {str(e)}]"

        data = attachment.get("data", "")
        if not data:
            return "[Empty attachment]"

        file_bytes = base64.urlsafe_b64decode(data + "==")

        # Try PDF text extraction
        try:
            text = pdf_extract_text(BytesIO(file_bytes))
            return text[:5000] if text else "[No text extractable from PDF]"
        except Exception:
            pass

        # Try decoding as plain text
        try:
            return file_bytes.decode("utf-8", errors="replace")[:5000]
        except Exception:
            return "[Binary attachment — cannot extract text]"
