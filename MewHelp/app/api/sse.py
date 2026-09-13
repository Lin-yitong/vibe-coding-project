import json


def _event(payload: object) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


def encode_delta(text: str) -> str:
    return _event({"delta": text})


def encode_done() -> str:
    return "data: [DONE]\n\n"


def encode_error(message: str) -> str:
    return _event({"error": {"code": "upstream_error", "message": message}})
