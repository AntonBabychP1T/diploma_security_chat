import asyncio
import re
from typing import Dict, Tuple
from unittest.mock import AsyncMock, MagicMock
from app.services.pii_service import PIIService
from app.services.secretary_service import SecretaryService
from app.services.secretary_tools import SecretaryTools
from app.schemas.secretary import EmailMessage, CalendarEvent, TimeSlot

# Mock Settings
import app.core.config
app.core.config.get_settings = MagicMock()
app.core.config.get_settings.return_value.SECRETARY_MAX_TURNS = 2

# Mock DB
async_session_mock = AsyncMock()

# Mock Provider
provider_mock = AsyncMock()
from app.providers import ProviderFactory
ProviderFactory.get_provider = MagicMock(return_value=provider_mock)

async def test_pii_service():
    print("Testing PIIService...")
    pii = PIIService()
    
    # Test 1: Basic Masking
    text = "My email is test@example.com and my other email is another@example.com"
    masked, mapping = pii.mask(text)
    print(f"Original: {text}")
    print(f"Masked: {masked}")
    print(f"Mapping: {mapping}")
    
    assert "{{EMAIL_1}}" in masked
    assert "{{EMAIL_2}}" in masked
    assert mapping["{{EMAIL_1}}"] == "test@example.com"
    assert "test@example.com" not in masked
    
    # Test 2: Unmasking
    unmasked = pii.unmask(masked, mapping)
    print(f"Unmasked: {unmasked}")
    assert unmasked == text
    
    # Test 3: Existing Mapping
    text2 = "Contact test@example.com again."
    masked2, mapping2 = pii.mask(text2, mapping=mapping)
    print(f"Text 2 Original: {text2}")
    print(f"Text 2 Masked: {masked2}")
    print(f"Mapping 2: {mapping2}")
    
    assert "{{EMAIL_1}}" in masked2
    assert mapping2["{{EMAIL_1}}"] == "test@example.com"
    
    # Test 4: Missing Braces Unmasking (LLM Robustness)
    text3 = "Please contact EMAIL_1 regarding this."
    unmasked3 = pii.unmask(text3, mapping)
    print(f"Missing Braces: '{text3}' -> '{unmasked3}'")
    assert "test@example.com" in unmasked3
    
    print("PIIService Tests Passed!")

async def test_secretary_service():
    print("\nTesting SecretaryService...")
    
    # Mock Tools Implementation
    tools_mock = MagicMock(spec=SecretaryTools)
    tools_mock.list_emails = AsyncMock(return_value="Found 1 email.")
    
    # Init Service
    service = SecretaryService(async_session_mock, 1)
    service.tools_impl = tools_mock # Replace with mock
    
    # Mock Provider Response
    # Turn 1: Call list_emails with a PII token in args
    tool_call = MagicMock()
    tool_call.id = "call_123"
    tool_call.function.name = "list_emails"
    tool_call.function.arguments = '{"account_label": "work", "filters": {"sender": "{{EMAIL_1}}"}}'
    
    response_1 = MagicMock()
    response_1.content = None
    response_1.tool_calls = [tool_call]
    
    # Turn 2: Final response
    response_2 = MagicMock()
    response_2.content = "I found emails from {{EMAIL_1}}."
    response_2.tool_calls = []
    
    provider_mock.generate.side_effect = [response_1, response_2]
    
    # Input with PII
    query = "Find emails from test@example.com"
    
    print(f"Query: {query}")
    final_response = await service.process_request(query)
    
    print(f"Final Response: {final_response}")
    
    # Assertions
    # 1. Check if PIIService logic worked in process_request
    # The provider should have received masked query
    call_args = provider_mock.generate.call_args_list[0]
    messages = call_args[0][0]
    last_user_msg = messages[-1]
    print(f"Message sent to LLM: {last_user_msg['content']}")
    assert "{{EMAIL_1}}" in last_user_msg['content']
    assert "test@example.com" not in last_user_msg['content']
    
    # 2. Check if tool was called with UNMASKED argument
    # The tool was called with '{{EMAIL_1}}' in args from LLM, but should be unmasked before execution
    execution_args = tools_mock.list_emails.call_args
    print(f"Tool Execution Args: {execution_args}")
    # tools_mock.list_emails(account_label, filters)
    filters_arg = execution_args[0][1] # second arg
    assert filters_arg['sender'] == "test@example.com"
    
    # 3. Check final response is unmasked
    assert "test@example.com" in final_response
    assert "{{EMAIL_1}}" not in final_response
    
    print("SecretaryService Tests Passed!")

if __name__ == "__main__":
    asyncio.run(test_pii_service())
    asyncio.run(test_secretary_service())
