import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.secretary_tools import SecretaryTools
from app.schemas.secretary import CalendarEvent
from datetime import datetime, timedelta

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def secretary_tools(mock_db):
    return SecretaryTools(mock_db, user_id=1)

@pytest.mark.asyncio
async def test_get_event(secretary_tools):
    mock_client = AsyncMock()
    mock_client.get_event.return_value = CalendarEvent(
        id="ev1",
        summary="Meeting",
        start=datetime.utcnow(),
        end=datetime.utcnow() + timedelta(hours=1),
        location="Room A",
        description="Discuss things",
        attendees=["a@b.com"]
    )
    secretary_tools._get_client = AsyncMock(return_value=mock_client)

    result = await secretary_tools.get_event("work", "ev1")
    
    assert "Event: Meeting" in result
    assert "Room A" in result
    mock_client.get_event.assert_called_once_with("ev1")

@pytest.mark.asyncio
async def test_update_event(secretary_tools):
    mock_client = AsyncMock()
    secretary_tools._get_client = AsyncMock(return_value=mock_client)
    
    result = await secretary_tools.update_event("work", "ev1", summary="New Title")
    
    assert "Event updated" in result
    mock_client.update_event.assert_called_once()
    args, kwargs = mock_client.update_event.call_args
    assert args[0] == "ev1"
    assert kwargs["summary"] == "New Title"

@pytest.mark.asyncio
async def test_delete_event(secretary_tools):
    mock_client = AsyncMock()
    secretary_tools._get_client = AsyncMock(return_value=mock_client)
    
    result = await secretary_tools.delete_event("work", "ev1")
    
    assert "Event deleted" in result
    mock_client.delete_event.assert_called_once_with("ev1", True)

@pytest.mark.asyncio
async def test_respond_to_invitation(secretary_tools):
    mock_client = AsyncMock()
    secretary_tools._get_client = AsyncMock(return_value=mock_client)
    
    result = await secretary_tools.respond_to_invitation("work", "ev1", "accepted")
    
    assert "Responded 'accepted'" in result
    mock_client.respond_to_invitation.assert_called_once_with("ev1", "accepted", None)

@pytest.mark.asyncio
async def test_get_next_event(secretary_tools):
    mock_client = AsyncMock()
    now = datetime.utcnow()
    mock_client.list_events.return_value = [
        CalendarEvent(
            id="ev1",
            summary="Next Meeting",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2)
        )
    ]
    secretary_tools._get_client = AsyncMock(return_value=mock_client)
    
    result = await secretary_tools.get_next_event("work")
    
    assert "Next event: Next Meeting" in result
