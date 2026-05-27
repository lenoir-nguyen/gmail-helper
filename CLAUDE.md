# Gmail Helper — CLAUDE.md

**Project**: Gmail Document Helper  
**Status**: Active Development  
**Last Updated**: 2026-05-27  
**Owner**: Personal use only (ndnduc@gmail.com)

---

## What This Project Does

A personal tool that connects to Gmail (read-only), extracts data from emails using a
multi-agent AI pipeline (OpenAI GPT-4o-mini), and populates Word (.docx) or Excel (.xlsx)
documents with the extracted data.

**User flow:**
1. Click "Connect Gmail" → one-click Google OAuth (identity + gmail.readonly)
2. Upload a Word or Excel document template
3. Type a natural language request ("Find all job application emails since April 1, 2026")
4. Download the populated document

---

## Architecture

```
frontend/   →  Next.js + Tailwind   →  Vercel
backend/    →  FastAPI (Python)     →  Railway
```

**No database.** Stateless — documents are processed in-memory and returned immediately.

---

## Gmail Permissions — STRICTLY READ-ONLY

OAuth scopes requested:
- `openid` — identity
- `userinfo.email` — user's email address
- `userinfo.profile` — user's name and avatar
- `gmail.readonly` — **read emails only — no write/send/delete ever**

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js 16 + Tailwind CSS | TypeScript, App Router |
| Backend | FastAPI (Python 3.11+) | Async, pydantic-settings |
| AI | OpenAI GPT-4o-mini | Extraction agent (no tool calls) |
| Gmail API | google-api-python-client | Read-only credentials |
| Word docs | python-docx | Read structure + populate via XML clone |
| Excel docs | openpyxl | Read structure + populate |
| Token storage | Browser localStorage | Personal use, no DB needed |

---

## Multi-Agent Pipeline

The backend uses three specialised agents that run in sequence:

```
Request
  │
  ▼
┌─────────────────────────────────────────────┐
│  Orchestrator  (services/agent.py)          │
│  Detects request type → routes to pipeline  │
└──────────────┬──────────────────────────────┘
               │
   ┌───────────▼───────────┐
   │  Agent 1              │  agents/search_agent.py
   │  Search Agent         │  • Runs 8 Gmail queries
   │  Pure Python, no LLM  │  • Deduplicates IDs
   │                       │  • Fetches email details (batches of 20)
   └───────────┬───────────┘
               │  list of raw emails
   ┌───────────▼───────────┐
   │  Agent 2              │  agents/extract_agent.py
   │  Extract Agent        │  • Batches of 25 emails per LLM call
   │  LLM, no tools        │  • Extracts structured fields
   │                       │  • Returns validated records
   └───────────┬───────────┘
               │  list of records
   ┌───────────▼───────────┐
   │  Agent 3              │  services/doc_service.py
   │  Doc Agent            │  • Fuzzy-matches headers → correct table/sheet
   │  Pure Python, no LLM  │  • Clones row XML (preserves styles)
   │                       │  • Stamps field values directly into XML
   └───────────────────────┘
```

**Why three agents?**
- **Agent 1** is deterministic — no LLM deciding when to stop searching; full pagination means no emails are missed beyond page 1
- **Agent 2** handles small focused batches — no context overflow or data loss
- **Agent 3** uses XML manipulation — reliable across complex styled documents

For non-job requests (invoices, orders, etc.) the Orchestrator falls back to
a classic tool-calling loop in `services/agent.py`.

---

## Project Structure

```
gmail-helper/
├── CLAUDE.md                    ← This file
├── README.md                    ← Setup & deployment guide
├── .env.example                 ← All required environment variables
│
├── backend/
│   ├── main.py                  ← FastAPI app factory, CORS (expose_headers set)
│   ├── config.py                ← Pydantic settings (env vars)
│   ├── requirements.txt
│   ├── Procfile                 ← Railway deployment
│   │
│   ├── agents/                  ← Multi-agent pipeline
│   │   ├── __init__.py
│   │   ├── search_agent.py      ← Agent 1: Gmail search + fetch (no LLM)
│   │   └── extract_agent.py     ← Agent 2: LLM field extraction (no tools)
│   │
│   ├── routers/
│   │   ├── auth.py              ← Google OAuth flow (/auth/google/*)
│   │   └── process.py          ← Main endpoint: upload + request → document
│   │
│   └── services/
│       ├── gmail_service.py     ← Gmail API wrapper (read-only)
│       ├── agent.py             ← Orchestrator + generic tool-calling fallback
│       └── doc_service.py      ← Agent 3: analyze + populate Word/Excel docs
│
└── frontend/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx             ← Main 4-step UI
    │   ├── auth-callback/
    │   │   └── page.tsx         ← Handles OAuth redirect, stores token
    │   └── components/
    │       ├── GmailConnect.tsx  ← Step 1: OAuth connect button
    │       ├── DocumentUpload.tsx ← Step 2: Drag & drop file upload
    │       ├── AgentRequest.tsx  ← Step 3: Natural language input
    │       └── ResultDownload.tsx ← Step 4: Download result
    ├── lib/
    │   ├── api.ts               ← Backend API calls
    │   └── auth.ts              ← Token helpers (localStorage)
    ├── next.config.ts
    └── tailwind.config.ts
```

---

## Environment Variables

### Backend (.env / Railway)
```
OPENAI_API_KEY=sk-...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://your-backend.railway.app/auth/google/callback
FRONTEND_URL=https://your-app.vercel.app
```

### Frontend (.env.local / Vercel)
```
NEXT_PUBLIC_BACKEND_URL=https://your-backend.railway.app
```

---

## Development Commands

```bash
# Backend  (port 8001 — port 8000 is used by another project)
cd backend
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Frontend
cd frontend
npm install
npm run dev                     # http://localhost:3000
```

---

## OAuth Flow

```
1. Frontend  → GET /auth/google/url
2. Backend   → returns Google OAuth authorization URL
3. User      → approves on Google consent screen
4. Google    → redirects to GOOGLE_REDIRECT_URI (backend callback)
5. Backend   → exchanges code → access_token, fetches user info
6. Backend   → redirects to FRONTEND_URL/auth-callback?token=...&email=...&name=...&picture=...
7. Frontend  → saves token to localStorage, redirects to /
```

Token expires after ~1 hour. User must disconnect and reconnect to refresh.

---

## Document Population — How It Works

### Header matching (fuzzy)
`doc_service.py` normalises both document headers and agent field names
(lowercase, strip punctuation/underscores, collapse whitespace), then scores
matches: exact = 3, contains = 2, word overlap = 1.

This means the agent can return `date_of_application` and it will correctly
map to a column header "Date of Application" in the document.

### Row writing (XML clone)
New rows are added by **deep-copying the last existing row's XML**, clearing
text nodes, then writing values directly into `<w:t>` elements.
This preserves all cell styles, borders, fonts and spacing.
`table.add_row()` (python-docx default) was discarded because it does not
carry over style XML in complex documents, leaving visually blank rows.

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
- Accepted/Rejected & Reason: leave empty

Sort results by date ascending (oldest first).
```

---

## Key Principles

- **Read-only forever**: Never request write scopes, never add write operations
- **Stateless**: No DB, no server-side file storage, in-memory only
- **Personal use**: Token in localStorage is fine — no auth system needed
- **Graceful errors**: Always show clear error messages, never crash silently
- **Deterministic search**: Python code runs all queries — don't rely on LLM to decide search strategy
