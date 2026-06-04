import os
import sys


sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.pii_service import PIIService


def test_masking():
    service = PIIService()

    text = (
        "My email is test@example.com and phone is +1 202-555-0199. "
        "Card: 1234 5678 1234 5678"
    )

    masked, mapping = service.mask(text)
    unmasked = service.unmask(masked, mapping)

    assert "test@example.com" not in masked
    assert "+1 202-555-0199" not in masked
    assert "1234 5678 1234 5678" not in masked
    assert "<EMAIL_1>" in masked
    assert "<PHONE_1>" in masked
    assert "<CARD_1>" in masked
    assert unmasked == text


def test_ukrainian_rental_request_masking():
    service = PIIService()

    text = (
        "Допоможи, будь ласка, написати ввічливу відповідь на лист. "
        "Мені написав менеджер з оренди квартири, Олександр Мельник, "
        "з пошти oleksandr.melnyk@example.com. Він просить підтвердити, "
        "чи я зможу приїхати на перегляд квартири завтра о 18:30 за адресою "
        "м. Київ, вул. Січових Стрільців, 41. Напиши відповідь, що я підтверджую "
        "зустріч, але прошу зателефонувати мені за номером +380 67 245 18 90, "
        "якщо час зміниться."
    )

    expected = (
        "Допоможи, будь ласка, написати ввічливу відповідь на лист. "
        "Мені написав менеджер з оренди квартири, <PERSON_1>, "
        "з пошти <EMAIL_1>. Він просить підтвердити, "
        "чи я зможу приїхати на перегляд квартири завтра о <TIME_1> за адресою "
        "<ADDRESS_1>. Напиши відповідь, що я підтверджую "
        "зустріч, але прошу зателефонувати мені за номером <PHONE_1>, "
        "якщо час зміниться."
    )

    masked, mapping = service.mask(text)

    assert masked == expected
    assert mapping["<PERSON_1>"] == "Олександр Мельник"
    assert mapping["<EMAIL_1>"] == "oleksandr.melnyk@example.com"
    assert mapping["<TIME_1>"] == "18:30"
    assert mapping["<ADDRESS_1>"] == "м. Київ, вул. Січових Стрільців, 41"
    assert mapping["<PHONE_1>"] == "+380 67 245 18 90"
    assert service.unmask(masked, mapping) == text


def test_legacy_tokens_are_normalized_and_reserved():
    service = PIIService()

    text = "Писав Олександр Мельник з {{EMAIL_1}}, копія на rent.owner@example.com."
    masked, mapping = service.mask(text)

    assert "{{EMAIL_1}}" not in masked
    assert "<EMAIL_1>" in masked
    assert "<EMAIL_2>" in masked
    assert "<PERSON_1>" in masked
    assert mapping["<EMAIL_2>"] == "rent.owner@example.com"


def test_unmask_supports_legacy_and_bare_tokens():
    service = PIIService()
    mapping = {"{{EMAIL_1}}": "test@example.com", "<PHONE_1>": "+380 67 245 18 90"}

    assert service.unmask("Email: <EMAIL_1>, phone: PHONE_1", mapping) == (
        "Email: test@example.com, phone: +380 67 245 18 90"
    )


def test_email_wrapped_in_angle_brackets_does_not_double_wrap():
    service = PIIService()

    text = "Contact <email@inside.brackets> today."
    masked, mapping = service.mask(text)

    assert masked == "Contact <EMAIL_1> today."
    assert mapping["<EMAIL_1>"] == "<email@inside.brackets>"
    assert service.unmask(masked, mapping) == text


if __name__ == "__main__":
    test_masking()
    test_ukrainian_rental_request_masking()
    test_legacy_tokens_are_normalized_and_reserved()
    test_unmask_supports_legacy_and_bare_tokens()
    test_email_wrapped_in_angle_brackets_does_not_double_wrap()
    print("Tests passed.")
