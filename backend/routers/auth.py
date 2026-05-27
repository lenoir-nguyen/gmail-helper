"""
Google OAuth 2.0 flow — identity + gmail.readonly only.

Endpoints:
  GET /auth/google/url       → returns the Google consent URL
  GET /auth/google/callback  → exchanges code for token, redirects to frontend
"""

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from config import settings, GMAIL_SCOPES

router = APIRouter()

# ─── helpers ──────────────────────────────────────────────────────────────────

def _build_flow() -> Flow:
    """Create a Google OAuth flow from env config."""
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri],
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )


# ─── routes ───────────────────────────────────────────────────────────────────

@router.get("/google/url")
async def get_google_auth_url():
    """Return the Google OAuth consent URL for the frontend to redirect to."""
    flow = _build_flow()
    authorization_url, _ = flow.authorization_url(
        access_type="online",       # No refresh token — re-auth when expired
        include_granted_scopes="true",
        prompt="select_account",    # Always show account picker
    )
    return {"url": authorization_url}


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    error: str = Query(None),
):
    """
    Google redirects here after user approves.
    Exchange code → access token → fetch user info → redirect to frontend.
    """
    if error:
        # User denied access or something went wrong
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth-callback?error={error}"
        )

    try:
        flow = _build_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        access_token = credentials.token

        # Fetch user profile (name, email, picture)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            user_info = resp.json()

        name = user_info.get("name", "")
        email = user_info.get("email", "")
        picture = user_info.get("picture", "")

        # Redirect to frontend — token stored in browser (localStorage)
        redirect_url = (
            f"{settings.frontend_url}/auth-callback"
            f"?token={access_token}"
            f"&email={email}"
            f"&name={name}"
            f"&picture={picture}"
        )
        return RedirectResponse(url=redirect_url)

    except Exception as exc:
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth-callback?error=auth_failed"
        )
