# Gmail Helper — Build Log & Conversation Summary

**Date**: 2026-05-27  
**Status**: Local development complete, ready for production deployment  
**Repo**: https://github.com/lenoir-nguyen/gmail-helper

---

## What We Built

A personal Gmail data extraction tool that:
1. Connects to Gmail via OAuth (read-only)
2. Searches emails using a multi-agent AI pipeline
3. Extracts structured data from email confirmations
4. Populates a Word (.docx) or Excel (.xlsx) document with the results
5. Returns the populated document as a download

Primary use case: **Job application tracking** — finds all "Thank you for applying" confirmation emails and fills a Word tracker document.

---

## Architecture

```
Frontend (Next.js 16 + Tailwind) → Vercel
Backend (FastAPI Python)         → Railway
```

### Three-Agent Pipeline

```
User Request
    │
    ▼
Orchestrator (services/agent.py)
    │
    ├─► Agent 1: Search Agent (agents/search_agent.py)
    │     - Pure Python, no LLM
    │     - Runs 18 Gmail search queries
    │     - Deduplicates email IDs
    │     - Fetches email details in batches of 20
    │     - Full pagination (follows nextPageToken — no 50-record cap)
    │
    ├─► Agent 2: Extract Agent (agents/extract_agent.py)
    │     - LLM only (GPT-4o-mini), no tools
    │     - Processes emails in batches of 25
    │     - Extracts: date, company, position, method
    │     - Returns structured JSON records
    │
    └─► Agent 3: Doc Agent (services/doc_service.py)
          - Pure Python, no LLM
          - Fuzzy header matching (score 0-3)
          - XML row cloning (NOT table.add_row())
          - Writes values directly into <w:t> XML elements
```

---

## Key Files

```
gmail-helper/
├── .gitignore                   ← excludes .env, node_modules, .venv
├── .env.example                 ← template (PYTHONUTF8=1 included)
├── README.md                    ← setup + deployment guide
├── CLAUDE.md                    ← full architecture docs for Claude Code
│
├── backend/
│   ├── main.py                  ← FastAPI app, CORS with expose_headers
│   ├── config.py                ← Pydantic settings
│   ├── requirements.txt
│   ├── Procfile                 ← Railway: "web: uvicorn main:app --host 0.0.0.0 --port $PORT"
│   ├── railway.json             ← Railway config
│   │
│   ├── agents/
│   │   ├── search_agent.py      ← Agent 1: 18 Gmail queries + pagination
│   │   └── extract_agent.py     ← Agent 2: LLM batch extraction
│   │
│   ├── routers/
│   │   ├── auth.py              ← GET /auth/google/url + GET /auth/google/callback
│   │   └── process.py          ← POST /process (main pipeline endpoint)
│   │
│   └── services/
│       ├── gmail_service.py     ← Gmail API wrapper, paginated search
│       ├── agent.py             ← Orchestrator + generic tool-calling fallback
│       └── doc_service.py      ← Word/Excel population via XML
│
└── frontend/
    ├── app/
    │   ├── page.tsx             ← 4-step UI
    │   ├── auth-callback/page.tsx ← OAuth redirect handler
    │   └── components/
    │       ├── GmailConnect.tsx
    │       ├── DocumentUpload.tsx
    │       ├── AgentRequest.tsx
    │       └── ResultDownload.tsx
    └── lib/
        ├── api.ts               ← processDocument(), getGmailAuthUrl()
        └── auth.ts              ← localStorage token helpers
```

---

## Local Development Setup

```
Backend port: 8001 (port 8000 is taken by another project: lenoir-assistant)
Frontend port: 3000
```

### Backend
```powershell
cd backend
.venv\Scripts\activate
uvicorn main:app --reload --port 8001
# OR with UTF-8 fix for Windows:
$env:PYTHONUTF8="1"; .\.venv\Scripts\uvicorn.exe main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
npm run dev
```

### Backend .env (already filled, never commit)
```
OPENAI_API_KEY=sk-...
GOOGLE_CLIENT_ID=911713640000-...
GOOGLE_CLIENT_SECRET=GOCSPX-...
GOOGLE_REDIRECT_URI=http://localhost:8001/auth/google/callback
FRONTEND_URL=http://localhost:3000
PYTHONUTF8=1
```

---

## Gmail OAuth Scopes (READ-ONLY FOREVER)

```python
GMAIL_SCOPES = [
    "openid",
    "userinfo.email",
    "userinfo.profile",
    "gmail.readonly",   # ← NEVER add write scopes
]
```

---

## The 18 Search Queries (search_agent.py)

For job application tracking, Agent 1 runs all of these:

```
"thank you for applying"
"thanks for applying"
"thank you for your application"
"thanks for your application"
"thank you for submitting your application"
"thank you for your recent application"
"we received your application"
"we've received your application"
"your application has been received"
"your application was received"
"application successfully submitted"
"successfully submitted your application"
"thank you for your interest" + (position OR role OR engineer OR developer...)
subject:application + (thank you OR received OR confirmation OR submitted)
subject:applying
subject:"your application"
subject:"application received"
subject:"application submitted"
subject:"application confirmation"
```

Each query is paginated — follows Gmail's `nextPageToken` until all results are fetched (no record cap).

---

## Document Population — How It Works

### Header matching (fuzzy, doc_service.py)
- Normalises text: lowercase, strip `_-/&,;:()'"`, collapse whitespace
- Scores matches: exact=3, contains=2, word overlap=1
- Agent field `date_of_application` → document header "Date of Application" → score 3 ✓

### Row writing (XML clone, NOT python-docx add_row)
```python
def _clone_row(table, row_data, col_map):
    template_tr = table.rows[-1]._tr
    new_tr = deepcopy(template_tr)           # copy last row's XML
    for t_el in new_tr.findall(f".//{_W}t"):
        t_el.text = ""                        # blank all text
    table._tbl.append(new_tr)               # attach to table
    # then write values directly into <w:t> elements
```

`table.add_row()` was abandoned because it creates cells with no style inheritance, resulting in blank rows in complex styled documents.

---

## Extracted Fields (Job Application Mode)

| Agent Field | Document Header |
|---|---|
| `date_of_application` | Date of Application |
| `method_of_application` | Method of Application |
| `company` | Company |
| `position` | Position |
| `expense` | Expense (always empty) |
| `interview_offer_of_employment` | Interview/Offer of Employment (always empty) |
| `accepted_rejected_reason` | Accepted/Rejected & Reason (always empty) |

---

## Ideal Prompt for Job Application Tracking

```
Find all job application confirmation emails since April 1, 2026. For each
application found, extract:
- Date of Application: the date the confirmation email was received (YYYY-MM-DD)
- Method of Application: how I applied (LinkedIn, Indeed, Company Website, Referral)
- Company: the company name
- Position: the job title / role I applied for
- Expense: leave empty
- Interview/Offer of Employment: leave empty
- Accepted/Rejected & Reason: classify as "waiting", "rejected", "interviewed", or "accepted"
  based on the email content

Sort results by date ascending (oldest first).
```

### Status Classification Rules (accepted_rejected_reason)

| Value | When to use |
|---|---|
| `waiting` | Standard confirmation — received, under review, we'll be in touch (DEFAULT) |
| `rejected` | Not moving forward, regret to inform, position filled, other candidates |
| `interviewed` | Interview invitation, phone screen, schedule a call, next steps |
| `accepted` | Job offer, offer letter, congratulations, welcome to the team |

---

## Issues Encountered & Fixed

| Issue | Root Cause | Fix |
|---|---|---|
| Port conflict | lenoir-assistant uses port 8000 | Backend runs on port 8001 |
| TPM rate limit 429 | gpt-4o too many tokens | Switched to gpt-4o-mini |
| 404 on Gmail API calls | Deleted/archived emails | try/except returning error dicts |
| Context length exceeded | Too many emails in one conversation | Multi-agent split: search Python, extract LLM |
| ChatCompletionMessage not serializable | Pydantic model in messages list | `.model_dump(exclude_none=True)` |
| Download always .xlsx | CORS missing `expose_headers` | Added `expose_headers=["Content-Disposition","X-Summary","X-Row-Count"]` |
| Only 15 records returned | Hard cap of 30 on search | Raised to 500 per query |
| Only 12-50 records | No Gmail pagination | Implemented `nextPageToken` loop |
| Blank rows in Word doc | `cell.text=` destroys style XML | XML deep-copy + direct `<w:t>` manipulation |
| charmap encoding error | Windows console can't encode `→` `…` | `PYTHONUTF8=1` + replaced Unicode in print() |
| Agent stops at 2-12 records | LLM loses track across many tool calls | Architectural fix: Python does searching, LLM only extracts |
| Extract agent skips records | INCLUDE/SKIP logic too strict | Changed to "extract from ALL emails, never skip" |

---

## CORS Configuration (main.py)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Summary", "X-Row-Count"],
)
```

`expose_headers` is critical — without it, the browser can't read `Content-Disposition` and the download always falls back to `result_timestamp.xlsx`.

---

## Production Deployment (TODO — next session)

### Backend → Railway
1. New project → Deploy from GitHub → `gmail-helper`
2. Root directory: `backend`
3. Environment variables:
   ```
   OPENAI_API_KEY=sk-...
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REDIRECT_URI=https://YOUR-APP.railway.app/auth/google/callback
   FRONTEND_URL=https://YOUR-APP.vercel.app
   PYTHONUTF8=1
   ```

### Frontend → Vercel
1. New project → Import `gmail-helper`
2. Root directory: `frontend`
3. Environment variable:
   ```
   NEXT_PUBLIC_BACKEND_URL=https://YOUR-APP.railway.app
   ```

### Google Cloud Console
After deploying, add to Authorized Redirect URIs:
- `https://YOUR-APP.railway.app/auth/google/callback`

---

## Current Results

- Local dev: fully working
- Job application tracking: ~150 records found (user's actual inbox count)
- Word document: populated correctly with all fields in right columns
- Download: returns correct .docx or .xlsx matching uploaded file type
- GitHub: https://github.com/lenoir-nguyen/gmail-helper (private repo)
