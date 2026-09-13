from collections.abc import Sequence
from functools import lru_cache

import tiktoken
from langchain_core.messages import BaseMessage


DEFAULT_ENCODING_NAME = "cl100k_base"


@lru_cache(maxsize=None)
def _get_encoding(encoding_name: str) -> tiktoken.Encoding:
    return tiktoken.get_encoding(encoding_name)


def count_message_tokens(
    messages: Sequence[BaseMessage], encoding_name: str = DEFAULT_ENCODING_NAME
) -> int:
    """Estimate message content tokens without asking the active chat model."""
    encoding = _get_encoding(encoding_name)
    return sum(len(encoding.encode(str(message.content))) for message in messages)
