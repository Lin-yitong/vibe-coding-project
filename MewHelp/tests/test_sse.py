from app.api.sse import encode_delta, encode_done, encode_error


def test_sse_encoding_is_protocol_exact() -> None:
    """Catch SSE events that corrupt Chinese text or the required done marker."""
    assert encode_delta("您好，") == 'data: {"delta":"您好，"}\n\n'
    assert encode_done() == "data: [DONE]\n\n"
    assert (
        encode_error("provider unavailable")
        == 'data: {"error":{"code":"upstream_error","message":"provider unavailable"}}\n\n'
    )
