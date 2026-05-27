"""
Main processing endpoint.

POST /process
  - Receives: document file (multipart) + user request text + Gmail token (header)
  - Returns: populated document (file download)

Everything is stateless — no files stored server-side.
"""

import json
from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response

from services.agent import GmailAgent
from services.doc_service import analyze_document, populate_document
from services.gmail_service import GmailService

router = APIRouter()


@router.post("")
async def process_request(
    file: UploadFile = File(..., description="Word (.docx) or Excel (.xlsx) document"),
    request: str = Form(..., description="Natural language request for data extraction"),
    authorization: str = Header(..., description="Bearer <gmail_access_token>"),
):
    """
    Full pipeline: analyze document → agent searches Gmail → populate document → return file.
    """

    # ── 1. Extract Gmail token from header ────────────────────────────────────
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header must be: Bearer <gmail_access_token>",
        )
    access_token = authorization.removeprefix("Bearer ").strip()

    # ── 2. Read uploaded file ─────────────────────────────────────────────────
    filename = file.filename or "document.xlsx"
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # ── 3. Analyze document structure ─────────────────────────────────────────
    try:
        doc_structure = analyze_document(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ── 4. Run the AI agent ────────────────────────────────────────────────────
    try:
        gmail_service = GmailService(access_token)
        agent = GmailAgent(gmail_service)
        agent_result = await agent.run(
            user_request=request,
            doc_structure=doc_structure,
        )
    except Exception as e:
        error_msg = str(e)
        # Surface common errors clearly
        if any(k in error_msg.lower() for k in ("invalid_grant", "401", "token expired", "invalid credentials")):
            raise HTTPException(
                status_code=401,
                detail="Gmail session expired. Please disconnect and reconnect your Gmail account.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {error_msg}",
        )

    # ── 5. Log agent result for debugging ────────────────────────────────────
    print(f"[process] agent summary: {agent_result.get('summary', '')}")
    print(f"[process] agent data count: {len(agent_result.get('data', []))}")
    print(f"[process] agent column_order: {agent_result.get('column_order', [])}")
    if agent_result.get("data"):
        print(f"[process] first row: {agent_result['data'][0]}")

    # ── 6. Check agent found something ───────────────────────────────────────
    if not agent_result.get("data"):
        summary = agent_result.get("summary", "")
        detail = (
            f"No matching emails found. {summary}".strip()
            if summary
            else (
                "No matching emails were found in Gmail for your request. "
                "Try broadening your search — for example, remove date filters "
                "or use fewer keywords."
            )
        )
        raise HTTPException(status_code=422, detail=detail)

    # ── 6. Populate the document ──────────────────────────────────────────────
    try:
        output_bytes = populate_document(file_bytes, filename, agent_result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document population error: {str(e)}",
        )

    # ── 6. Return the populated file ──────────────────────────────────────────
    ext = filename.lower().rsplit(".", 1)[-1]
    content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if ext in ("xlsx", "xls")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    # Build output filename: "my_template_filled.xlsx"
    base = filename.rsplit(".", 1)[0]
    output_filename = f"{base}_filled.{ext}"

    return Response(
        content=output_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{output_filename}"',
            "X-Summary": agent_result.get("summary", ""),
            "X-Row-Count": str(len(agent_result.get("data", []))),
        },
    )
