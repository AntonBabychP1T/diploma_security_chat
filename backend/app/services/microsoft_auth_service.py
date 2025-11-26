import httpx
from urllib.parse import urlencode
from app.core.config import get_settings
from typing import Dict, Any

settings = get_settings()

class MicrosoftAuthService:
    # Using v2.0 endpoint
    MICROSOFT_AUTH_BASE = "https://login.microsoftonline.com"
    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
    
    SCOPES = [
        "openid",
        "profile",
        "offline_access",
        "User.Read",
        "Mail.Read",
        "Calendars.Read",
        # "OnlineMeetings.ReadWrite" # Add later if needed or requested
    ]

    @classmethod
    def get_authorization_url(cls, state: str, redirect_uri: str) -> str:
        if not settings.MICROSOFT_CLIENT_ID:
            raise ValueError("Microsoft Client ID must be configured.")
        if not redirect_uri:
            raise ValueError("redirect_uri must be provided.")

        tenant = settings.MICROSOFT_TENANT_ID or "common"
        base_url = f"{cls.MICROSOFT_AUTH_BASE}/{tenant}/oauth2/v2.0/authorize"

        params = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(cls.SCOPES),
            "state": state,
            # "prompt": "consent" # Optional, forces consent screen
        }
        return f"{base_url}?{urlencode(params)}"

    @classmethod
    async def exchange_code_for_token(cls, code: str, redirect_uri: str) -> Dict[str, Any]:
        if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
            raise ValueError("Microsoft Client ID and Secret must be configured.")
        
        tenant = settings.MICROSOFT_TENANT_ID or "common"
        token_url = f"{cls.MICROSOFT_AUTH_BASE}/{tenant}/oauth2/v2.0/token"

        data = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(cls.SCOPES) 
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            return response.json()

    @classmethod
    async def refresh_access_token(cls, refresh_token: str) -> Dict[str, Any]:
        if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
            raise ValueError("Microsoft Client ID and Secret must be configured.")

        tenant = settings.MICROSOFT_TENANT_ID or "common"
        token_url = f"{cls.MICROSOFT_AUTH_BASE}/{tenant}/oauth2/v2.0/token"

        data = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(cls.SCOPES)
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            return response.json()

    @classmethod
    async def get_user_profile(cls, access_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{cls.GRAPH_API_BASE}/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
