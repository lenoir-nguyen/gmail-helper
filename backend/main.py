import sys

# Force UTF-8 stdout/stderr on Windows (default is charmap which rejects many Unicode chars)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import auth, process

app = FastAPI(
    title="Gmail Helper API",
    description="Personal Gmail data extractor — read-only access",
    version="1.0.0",
)

# Allow requests from the frontend (Vercel or localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    # Expose custom headers so the browser can read them in JS
    expose_headers=["Content-Disposition", "X-Summary", "X-Row-Count"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(process.router, prefix="/process", tags=["process"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gmail-helper"}
