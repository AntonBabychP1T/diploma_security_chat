import httpx
from urllib.parse import urlencode
from app.core.config import get_settings
from typing import Dict, Any

settings = get_settings()

class GoogleAuthService:
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",  # For archiving/labeling
        "https://www.googleapis.com/auth/gmail.compose", # For creating drafts
        "https://www.googleapis.com/auth/calendar",  # Full calendar access to create/edit events
        "https://www.googleapis.com/auth/userinfo.email",
        "openid"
    ]

    @classmethod
    def get_authorization_url(cls, state: str, redirect_uri: str) -> str:
        if not settings.GOOGLE_CLIENT_ID:
            raise ValueError("Google Client ID must be configured.")
        if not redirect_uri:
            raise ValueError("redirect_uri must be provided.")

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(cls.SCOPES),
            "access_type": "offline", # Important for refresh token
            "prompt": "consent",      # Force consent to get refresh token
            "state": state,
            "include_granted_scopes": "true"
        }
        return f"{cls.GOOGLE_AUTH_URL}?{urlencode(params)}"

    @classmethod
    async def exchange_code_for_token(cls, code: str, redirect_uri: str) -> Dict[str, Any]:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Google Client ID and Secret must be configured.")
        if not redirect_uri:
            raise ValueError("redirect_uri must be provided.")

        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(cls.GOOGLE_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()

    @classmethod
    async def refresh_access_token(cls, refresh_token: str) -> Dict[str, Any]:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Google Client ID and Secret must be configured.")

        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(cls.GOOGLE_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()

    @classmethod
    async def get_user_info(cls, access_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
