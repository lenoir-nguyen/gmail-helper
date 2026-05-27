# Gmail Helper

Extract data from your Gmail and populate Word/Excel documents — personal use, read-only.

---

## How It Works

1. **Connect Gmail** — one-click Google OAuth (`gmail.readonly` — read only, never writes)
2. **Upload document** — drop a `.docx` or `.xlsx` template
3. **Type your request** — e.g. *"Find all job application emails since April 1, 2026"*
4. **Download result** — get your document populated with the extracted data

### Under the hood — three-agent pipeline

```
Your request
    │
    ▼
Agent 1 — Search Agent (Python, no LLM)
  Runs 8 Gmail queries, deduplicates IDs, fetches email details
    │
    ▼
Agent 2 — Extract Agent (GPT-4o-mini, no tools)
  Processes emails in batches of 25, extracts structured fields
    │
    ▼
Agent 3 — Doc Agent (Python, no LLM)
  Fuzzy-maps fields → document columns, writes rows via XML clone
    │
    ▼
Populated .docx / .xlsx download
```

---

## Quick Start

### 1. Google Cloud Setup (~10 minutes, one-time)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. **Create project** — name it "gmail-helper"
3. **Enable APIs**: Gmail API + People API
4. **OAuth consent screen**: External → add your email as a test user
5. **Credentials** → Create OAuth 2.0 Client ID (Web application)
   - Authorized redirect URIs:
     - `http://localhost:8001/auth/google/callback` ← local dev
     - `https://YOUR-APP.railway.app/auth/google/callback` ← production
6. Copy the **Client ID** and **Client Secret**

---

### 2. Local Development

**Backend** (port 8001):
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

pip install -r requirements.txt

# Copy and fill in the env file
cp .env.example .env
# Edit .env: OPENAI_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
#            GOOGLE_REDIRECT_URI=http://localhost:8001/auth/google/callback,
#            FRONTEND_URL=http://localhost:3000

uvicorn main:app --reload --port 8001
```

**Frontend**:
```bash
cd frontend
npm install

# .env.local is already set to http://localhost:8001
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

### 3. Deploy — Backend → Railway

1. Push repo to GitHub
2. [Railway](https://railway.app) → New Project → Deploy from GitHub
3. Set **Root Directory** to `backend`
4. Add environment variables:
   ```
   OPENAI_API_KEY=sk-...
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REDIRECT_URI=https://YOUR-APP.railway.app/auth/google/callback
   FRONTEND_URL=https://YOUR-APP.vercel.app
   ```
5. Deploy → copy your Railway URL

---

### 4. Deploy — Frontend → Vercel

1. [Vercel](https://vercel.com) → New Project → Import from GitHub
2. Set **Root Directory** to `frontend`
3. Add environment variable:
   ```
   NEXT_PUBLIC_BACKEND_URL=https://YOUR-APP.railway.app
   ```
4. Deploy

---

### 5. Update Google Cloud after deployment

Go back to Google Cloud Console → Credentials → your OAuth client and add:
- `https://YOUR-APP.railway.app/auth/google/callback`

---

## Security

- Gmail access is **strictly read-only** (`gmail.readonly` scope)
- The app can **never** send, delete, label, or modify emails
- Your OAuth token is stored only in your browser's localStorage — no server DB
- Documents are processed in-memory and immediately discarded — never stored
- All traffic goes through HTTPS (Railway + Vercel)

---

## Ideal Prompt — Job Application Tracking

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

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "Gmail session expired" | OAuth token expired (~1 hour TTL) | Disconnect and reconnect Gmail |
| "No matching emails found" | Wrong date or no emails match queries | Check the date format; try a broader request |
| Blank rows in Word doc | — | Update to latest backend (XML clone approach) |
| Only recent emails returned | Old search cap (fixed) | Ensure backend is latest version |
