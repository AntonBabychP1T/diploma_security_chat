import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add backend to path and change CWD to find .env
backend_path = os.path.join(os.getcwd(), "backend")
if os.path.exists(backend_path):
    os.chdir(backend_path)
    sys.path.append(backend_path)
else:
    # Already in backend?
    sys.path.append(os.getcwd())

# Set dummy credentials for verification
os.environ["MICROSOFT_CLIENT_ID"] = "dummy_client_id"
os.environ["MICROSOFT_CLIENT_SECRET"] = "dummy_client_secret"

from app.models.microsoft_account import MicrosoftAccount
from app.services.microsoft_auth_service import MicrosoftAuthService
from app.services.microsoft_graph import MicrosoftGraphClient
from app.services.secretary_tools import SecretaryTools
from app.services.interfaces import MailCalendarProvider
from app.routers.microsoft_auth import router as ms_router

async def verify_imports():
    print("✅ Imports successful")

async def verify_graph_client():
    # Mock client
    client = MicrosoftGraphClient("dummy_token")
    assert isinstance(client, MailCalendarProvider) # Check protocol compliance (duck typing check)
    print("✅ MicrosoftGraphClient implements MailCalendarProvider protocol (implicitly)")

async def verify_auth_service():
    url = MicrosoftAuthService.get_authorization_url("state", "http://localhost/callback")
    assert "client_id" in url
    assert "scope" in url
    print(f"✅ Auth URL generated: {url}")

async def main():
    await verify_imports()
    await verify_graph_client()
    await verify_auth_service()

if __name__ == "__main__":
    asyncio.run(main())
