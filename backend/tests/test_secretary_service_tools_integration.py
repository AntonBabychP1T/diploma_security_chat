import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.secretary_service import SecretaryService

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def secretary_service(mock_db):
    service = SecretaryService(mock_db, user_id=1)
    service.provider = AsyncMock()
    service.tools_impl = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_process_request_calls_get_email(secretary_service):
    # Mock LLM response to call get_email
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "get_email"
    mock_tool_call.function.arguments = '{"message_id": "123"}'
    mock_tool_call.id = "call_1"
    
    mock_response = MagicMock()
    mock_response.content = None
    mock_response.tool_calls = [mock_tool_call]
    
    secretary_service.provider.generate.side_effect = [
        mock_response, # First turn returns tool call
        MagicMock(content="Here is the email", tool_calls=[]) # Second turn returns final answer
    ]
    
    secretary_service.tools_impl.get_email.return_value = "Email content"
    
    response = await secretary_service.process_request("Read email 123")
    
    assert response == "Here is the email"
    secretary_service.tools_impl.get_email.assert_called_once_with("work", "123")

@pytest.mark.asyncio
async def test_process_request_calls_create_event(secretary_service):
    # Mock LLM response to call create_event
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "create_event"
    mock_tool_call.function.arguments = '{"summary": "Meeting", "start_time": "2023-01-01T10:00:00", "end_time": "2023-01-01T11:00:00"}'
    mock_tool_call.id = "call_2"
    
    mock_response = MagicMock()
    mock_response.content = None
    mock_response.tool_calls = [mock_tool_call]
    
    secretary_service.provider.generate.side_effect = [
        mock_response,
        MagicMock(content="Event created", tool_calls=[])
    ]
    
    secretary_service.tools_impl.create_event.return_value = "Event created successfully"
    
    response = await secretary_service.process_request("Schedule meeting")
    
    assert response == "Event created"
    secretary_service.tools_impl.create_event.assert_called_once()
