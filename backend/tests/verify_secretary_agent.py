import asyncio
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, AsyncMock
from app.services.secretary_service import SecretaryService
from app.models.google_account import GoogleAccount
from app.schemas.secretary import EmailMessage, CalendarEvent
from datetime import datetime

# Mock Provider Response with Tool Calls
class MockToolCall:
    def __init__(self, name, args, id="call_123"):
        self.function = MagicMock()
        self.function.name = name
        self.function.arguments = json.dumps(args)
        self.id = id
    
    def model_dump(self):
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.function.name,
                "arguments": self.function.arguments
            }
        }

async def mock_provider_generate(messages, options=None):
    last_msg = messages[-1]
    
    # 1. User asks for emails -> Assistant calls list_emails
    if last_msg["role"] == "user" and "emails" in last_msg["content"].lower():
        return MagicMock(
            content=None,
            tool_calls=[MockToolCall("list_emails", {"filters": {"is_unread": True}})]
        )
    
    # 2. Tool returns result -> Assistant summarizes
    if last_msg["role"] == "tool" and last_msg["tool_call_id"] == "call_123":
        return MagicMock(
            content="You have 1 unread email from Boss.",
            tool_calls=None
        )

    return MagicMock(content="I don't know.", tool_calls=None)

async def run_verification():
    print("Running Secretary Agent Verification...")
    
    # Mock DB
    mock_db = AsyncMock()
    
    # Mock Google Account
    mock_account = GoogleAccount(
        id=1, user_id=1, email="test@example.com", 
        label="work", access_token="fake", token_expiry=datetime.utcnow()
    )
    
    # Mock Service
    service = SecretaryService(mock_db, user_id=1)
    service.get_connected_accounts = AsyncMock(return_value=[mock_account])
    
    # Mock Provider
    service.provider = MagicMock()
    service.provider.generate = AsyncMock(side_effect=mock_provider_generate)
    
    # Mock Tools Implementation
    service.tools_impl = AsyncMock()
    service.tools_impl.list_emails.return_value = "Found 1 email: From Boss"
    
    # Test 1: Get Emails Flow
    print("\nTest 1: Agent Loop (Get Emails)")
    response = await service.process_request("Show me unread emails")
    print(f"Final Response: {response}")
    
    # Verify tool was called
    service.tools_impl.list_emails.assert_called_once()
    print("Tool 'list_emails' was called successfully.")

if __name__ == "__main__":
    asyncio.run(run_verification())
