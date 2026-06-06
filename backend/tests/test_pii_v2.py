import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.pii_service import PIIService
from app.services.secretary_service import SecretaryService


def test_v2_mask_and_legacy_unmask_compat():
    pii = PIIService(token_format="v2", pii_v2_enabled=True, contextual_numeric_ids=True)
    text = "Contact test@example.com for details."
    masked, mapping = pii.mask(text)

    assert "<<PII:EMAIL:" in masked
    assert "test@example.com" not in masked
    assert mapping

    # Legacy and model-normalized placeholders remain unmaskable for compatibility.
    legacy = "EMAIL_1 and {{EMAIL_1}} and PII:EMAIL:0001 and <PII:EMAIL:0001>"
    unmasked = pii.unmask(legacy, mapping)
    assert unmasked.count("test@example.com") == 4


def test_precision_false_positive_controls():
    pii = PIIService(token_format="v2", pii_v2_enabled=True, contextual_numeric_ids=True)

    masked_swift, _ = pii.mask("PASSWORD and ABCDEFGH should stay unchanged.")
    assert "PASSWORD" in masked_swift
    assert "ABCDEFGH" in masked_swift

    masked_number, _ = pii.mask("Invoice number 1234567890 should stay visible.")
    assert "1234567890" in masked_number

    masked_with_context, mapping = pii.mask("My INN is 1234567890")
    assert any("RNOKPP" in token for token in mapping.keys())


def test_card_luhn_validation():
    pii = PIIService(token_format="v2", pii_v2_enabled=True)

    invalid_masked, invalid_mapping = pii.mask("Card 1234 5678 1234 5678")
    assert invalid_mapping == {}
    assert "1234 5678 1234 5678" in invalid_masked

    valid_masked, valid_mapping = pii.mask("Card 4242 4242 4242 4242")
    assert any("CARD" in token for token in valid_mapping.keys())
    assert "4242 4242 4242 4242" not in valid_masked


def test_ukrainian_bank_request_masks_contextual_pii():
    pii = PIIService(token_format="v2", pii_v2_enabled=True, contextual_numeric_ids=True)
    name = "\u0410\u043d\u0442\u043e\u043d \u0411\u0430\u0431\u0438\u0447"
    address = (
        "\u043c. \u041a\u0438\u0457\u0432, \u0432\u0443\u043b. "
        "\u0410\u043d\u0442\u043e\u043d\u043e\u0432\u0438\u0447\u0430, "
        "\u0431\u0443\u0434. 72, \u043a\u0432. 18"
    )
    rnokpp_label = "\u0420\u041d\u041e\u041a\u041f\u041f"
    id_card_label = "ID-\u043a\u0430\u0440\u0442\u043a\u0438"
    text = (
        f"Person: {name}. Address: {address}. Phone: +380 67 245 81 39. "
        "Email: antonbabych03@gmail.com. At 09:42 card 4111 1111 1111 1111 "
        f"IBAN UA213223130000026007233566001. {rnokpp_label} 3184512769, "
        f"number {id_card_label} 004582731."
    )

    masked, mapping = pii.mask(text)
    mapped_types = {token.split(":")[1] for token in mapping}

    assert {
        "PERSON",
        "ADDRESS",
        "PHONE",
        "EMAIL",
        "TIME",
        "CARD",
        "IBAN",
        "RNOKPP",
        "PASSPORT_ID",
    }.issubset(mapped_types)
    for value in (
        name,
        address,
        "+380 67 245 81 39",
        "antonbabych03@gmail.com",
        "09:42",
        "4111 1111 1111 1111",
        "UA213223130000026007233566001",
        "3184512769",
        "004582731",
    ):
        assert value not in masked
    assert pii.unmask(masked, mapping) == text


def test_stream_unmask_with_split_token():
    pii = PIIService(token_format="v2", pii_v2_enabled=True)
    _, mapping = pii.mask("Reach me at test@example.com")
    token = next(iter(mapping.keys()))

    session = pii.create_session(mapping=mapping)
    chunk1 = f"Hello {token[:8]}"
    chunk2 = f"{token[8:]} world"

    part1 = session.unmask_chunk(chunk1)
    part2 = session.unmask_chunk(chunk2)
    tail = session.flush_unmask_tail()
    full = part1 + part2 + tail

    assert token not in full
    assert full == "Hello test@example.com world"


def test_stream_unmask_with_single_angle_v2_token():
    pii = PIIService(token_format="v2", pii_v2_enabled=True)
    _, mapping = pii.mask("Reach me at test@example.com")

    session = pii.create_session(mapping=mapping)
    part1 = session.unmask_chunk("Email: <PII:EMAIL")
    part2 = session.unmask_chunk(":0001>.")
    tail = session.flush_unmask_tail()
    full = part1 + part2 + tail

    assert "<PII:EMAIL:0001>" not in full
    assert full == "Email: test@example.com."


def test_stream_unmask_with_model_normalized_v2_tokens():
    pii = PIIService(token_format="v2", pii_v2_enabled=True)
    _, mapping = pii.mask("Reach me at test@example.com")

    session = pii.create_session(mapping=mapping)
    chunks = [
        "Email: << PII : EMAIL",
        " : 1 >>, also < PII : EMAIL : 1 > and PII:EMAIL:1.",
    ]

    full = "".join(session.unmask_chunk(chunk) for chunk in chunks)
    full += session.flush_unmask_tail()

    assert "PII:EMAIL" not in full
    assert full == "Email: test@example.com, also test@example.com and test@example.com."


@pytest.mark.asyncio
async def test_secretary_tool_args_unmask_and_result_roundtrip():
    mock_db = AsyncMock()
    service = SecretaryService(mock_db, user_id=1)
    service.pii = PIIService(token_format="v2", pii_v2_enabled=True, contextual_numeric_ids=True)
    service.provider = AsyncMock()
    service.tools_impl = AsyncMock()
    service.tools_impl.list_emails.return_value = "Found one email from test@example.com"

    service.provider.generate.side_effect = [
        MagicMock(
            content=None,
            tool_calls=[
                {
                    "id": "call_1",
                    "function": {
                        "name": "list_emails",
                        "arguments": json.dumps(
                            {
                                "account_label": "work",
                                "filters": {"sender": "<<PII:EMAIL:0001>>"},
                            }
                        ),
                    },
                }
            ],
        ),
        MagicMock(content="Done: <<PII:EMAIL:0001>>", tool_calls=[]),
    ]

    response = await service.process_request("Find emails from test@example.com")

    service.tools_impl.list_emails.assert_called_once()
    _, filters = service.tools_impl.list_emails.call_args[0]
    assert filters["sender"] == "test@example.com"
    assert "test@example.com" in response
    assert "<<PII:EMAIL:0001>>" not in response
