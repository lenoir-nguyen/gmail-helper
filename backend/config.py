from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI
    openai_api_key: str

    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    # URLs
    frontend_url: str = "http://localhost:3000"


settings = Settings()

# Gmail OAuth scopes — READ ONLY, no write permissions
GMAIL_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",  # ← strictly read-only
]
