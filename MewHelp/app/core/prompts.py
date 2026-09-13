from langchain_core.prompts import ChatPromptTemplate


SYSTEM_PROMPT = """你是电商售后客服。
禁止编造订单、物流、退款状态和平台规则。
信息不足时，主动追问订单号与关键信息。
不要承诺具体赔付或处理时效。
语气礼貌、简洁，并给出用户可以执行的下一步。
超出客服范围时，明确说明并引导用户寻求合适的帮助。"""

CUSTOMER_CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", "{message}")]
)

EXTRACT_TICKET_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """从用户提供的售后描述中提取工单字段。
仅能依据原文明确表达的信息填充字段；不得推测或补充事实。
原文未明确给出的字段必须使用 JSON null。""",
        ),
        ("human", "{text}"),
    ]
)
