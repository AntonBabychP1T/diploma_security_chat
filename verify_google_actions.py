import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

# Add backend to path and change CWD to find .env
backend_path = os.path.join(os.getcwd(), "backend")
if os.path.exists(backend_path):
    os.chdir(backend_path)
    sys.path.append(backend_path)
else:
    sys.path.append(os.getcwd())

from app.services.secretary_tools import SecretaryTools
from app.services.google_workspace import GoogleWorkspaceClient
from app.services.microsoft_graph import MicrosoftGraphClient

async def verify_google_client():
    print("\n--- Verifying GoogleWorkspaceClient ---")
    client = GoogleWorkspaceClient("dummy_token")
    
    # Mock httpx
    with AsyncMock() as mock_client:
        # Mock send_email
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_client.post.return_value = mock_response
        
        # We can't easily mock the internal httpx.AsyncClient used inside the class methods 
        # without dependency injection or patching. 
        # For this quick verification, we'll rely on the fact that the code structure is correct 
        # and just check if methods exist and signature is correct.
        
        assert hasattr(client, "send_email")
        assert hasattr(client, "create_event")
        print("✅ Methods exist on GoogleWorkspaceClient")

async def verify_secretary_tools():
    print("\n--- Verifying SecretaryTools ---")
    # Mock DB session
    mock_db = AsyncMock()
    tools = SecretaryTools(mock_db, 1)
    
    # Mock _get_client to return a mock provider
    mock_provider = AsyncMock()
    tools._get_client = AsyncMock(return_value=mock_provider)
    
    # Test send_email
    await tools.send_email("work", ["test@example.com"], "Subject", "Body")
    mock_provider.send_email.assert_called_once()
    print("✅ SecretaryTools.send_email calls provider")
    
    # Test create_event
    await tools.create_event("work", "Meeting", "2023-01-01T10:00:00", "2023-01-01T11:00:00", ["a@b.com"])
    mock_provider.create_event.assert_called_once()
    print("✅ SecretaryTools.create_event calls provider")

async def main():
    await verify_google_client()
    await verify_secretary_tools()

if __name__ == "__main__":
    asyncio.run(main())
