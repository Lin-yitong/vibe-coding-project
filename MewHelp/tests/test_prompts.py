from langchain_core.messages import HumanMessage, SystemMessage

from app.core.prompts import CUSTOMER_CHAT_PROMPT, EXTRACT_TICKET_PROMPT


def test_customer_prompt_gives_safe_next_step_for_incomplete_request() -> None:
    """Catch a customer prompt that may invent case facts instead of requesting them."""
    messages = CUSTOMER_CHAT_PROMPT.format_messages(message="我的商品有问题")

    system = messages[0]
    assert isinstance(system, SystemMessage)
    assert "订单" in system.content
    assert "关键信息" in system.content
    assert "禁止编造" in system.content
    assert "物流" in system.content
    assert "退款" in system.content
    assert messages[-1] == HumanMessage(content="我的商品有问题")


def test_extraction_prompt_requires_explicit_source_facts_and_json_null() -> None:
    """Catch extraction guidance that permits unsupported field values."""
    messages = EXTRACT_TICKET_PROMPT.format_messages(text="商品有问题，想处理")

    system = messages[0]
    assert isinstance(system, SystemMessage)
    assert "仅" in system.content
    assert "原文" in system.content
    assert "JSON null" in system.content
    assert messages[-1] == HumanMessage(content="商品有问题，想处理")
