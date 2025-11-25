import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, AsyncMock
from app.services.secretary_service import SecretaryService
from app.models.google_account import GoogleAccount
from app.schemas.secretary import SecretaryIntent, IntentType, EmailMessage, CalendarEvent, TimeSlot
from datetime import datetime

async def mock_provider_generate(messages, options=None):
    # Mock LLM response based on input
    content = messages[-1]["content"]
    
    if "json_object" in str(options):
        # Intent parsing mock
        if "emails" in content.lower():
            return MagicMock(content='{"intent_type": "get_emails", "account_label": "all", "email_filters": {"is_unread": true}, "original_query": "' + content + '"}')
        elif "calendar" in content.lower() or "events" in content.lower():
            return MagicMock(content='{"intent_type": "get_events", "account_label": "work", "date_range": {"relative_description": "today"}, "original_query": "' + content + '"}')
        else:
            return MagicMock(content='{"intent_type": "unknown", "original_query": "' + content + '"}')
    else:
        # Summarization mock
        return MagicMock(content=f"Summary of: {content[:50]}...")

async def run_verification():
    print("Running Secretary Verification...")
    
    # Mock DB
    mock_db = AsyncMock()
    
    # Mock Google Account
    mock_account = GoogleAccount(
        id=1, user_id=1, email="test@example.com", 
        label="work", access_token="fake", token_expiry=datetime.utcnow()
    )
    
    # Mock Service methods
    service = SecretaryService(mock_db, user_id=1)
    service.get_connected_accounts = AsyncMock(return_value=[mock_account])
    service.provider = MagicMock()
    service.provider.generate = AsyncMock(side_effect=mock_provider_generate)
    
    # Mock Google Client
    mock_client = AsyncMock()
    mock_client.list_emails.return_value = [
        EmailMessage(id="1", thread_id="1", subject="Test Email", sender="boss@work.com", snippet="Work hard", date=datetime.utcnow(), is_read=False)
    ]
    mock_client.list_events.return_value = [
        CalendarEvent(id="1", summary="Meeting", start=datetime.utcnow(), end=datetime.utcnow(), attendees=[])
    ]
    service._get_client_for_account = AsyncMock(return_value=mock_client)
    
    # Test 1: Get Emails
    print("\nTest 1: Get Emails")
    response = await service.process_request("Show me unread emails")
    print(f"Response: {response}")
    
    # Test 2: Get Events
    print("\nTest 2: Get Events")
    response = await service.process_request("What's on my calendar?")
    print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(run_verification())
