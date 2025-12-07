import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.secretary_tools import SecretaryTools
from app.schemas.secretary import EmailMessage
from datetime import datetime

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def secretary_tools(mock_db):
    return SecretaryTools(mock_db, user_id=1)

@pytest.mark.asyncio
async def test_get_email(secretary_tools):
    # Mock client
    mock_client = AsyncMock()
    mock_client.get_email.return_value = EmailMessage(
        id="123",
        thread_id="t1",
        subject="Test Subject",
        sender="test@example.com",
        snippet="Hello world",
        date=datetime.utcnow(),
        is_read=True,
        link="http://link"
    )
    secretary_tools._get_client = AsyncMock(return_value=mock_client)

    result = await secretary_tools.get_email("work", "123")
    
    assert "From: test@example.com" in result
    assert "Subject: Test Subject" in result
    mock_client.get_email.assert_called_once_with("123")

@pytest.mark.asyncio
async def test_reply_email(secretary_tools):
    mock_client = AsyncMock()
    secretary_tools._get_client = AsyncMock(return_value=mock_client)
    
    result = await secretary_tools.reply_email("work", "123", "Got it", reply_all=True)
    
    assert "Reply sent" in result
    mock_client.reply_email.assert_called_once_with("123", "Got it", True)

@pytest.mark.asyncio
async def test_forward_email(secretary_tools):
    mock_client = AsyncMock()
    secretary_tools._get_client = AsyncMock(return_value=mock_client)
    
    result = await secretary_tools.forward_email("work", "123", ["boss@example.com"], "FYI")
    
    assert "Email forwarded" in result
    mock_client.forward_email.assert_called_once_with("123", ["boss@example.com"], "FYI")

@pytest.mark.asyncio
async def test_delete_emails(secretary_tools):
    mock_client = AsyncMock()
    mock_client.delete_emails.return_value = {"count": 2}
    secretary_tools._get_client = AsyncMock(return_value=mock_client)
    
    result = await secretary_tools.delete_emails("work", ["123", "456"], hard_delete=False)
    
    assert "Deleted 2 emails" in result
    mock_client.delete_emails.assert_called_once_with(["123", "456"], False)
