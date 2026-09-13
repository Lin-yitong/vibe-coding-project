from langchain_core.messages import SystemMessage

from app.core.memory import SessionStore


def test_history_keeps_newest_complete_pair_only() -> None:
    """Catch a store that retains an older pair or a half-pair past budget."""
    store = SessionStore(token_budget=8)
    store.commit("s", "old user", "old assistant")
    store.commit("s", "new user", "new assistant")

    messages = store.build_messages(
        "s", "current", SystemMessage("system"), lambda items: len(items) * 2
    )

    assert [message.content for message in messages] == [
        "system",
        "new user",
        "new assistant",
        "current",
    ]


def test_history_always_keeps_system_and_current_message_over_budget() -> None:
    """Catch trimming that removes prompt-critical messages when they exceed budget."""
    store = SessionStore(token_budget=1)
    store.commit("s", "previous user", "previous assistant")

    messages = store.build_messages(
        "s", "current", SystemMessage("system"), lambda items: len(items) * 10
    )

    assert [message.content for message in messages] == ["system", "current"]


def test_history_does_not_skip_a_too_large_newest_pair_for_an_older_pair() -> None:
    """Catch a non-contiguous history that omits a newer turn but retains an old one."""
    store = SessionStore(token_budget=20)
    store.commit("s", "old", "pair")
    store.commit("s", "very long newest user", "very long newest assistant")

    messages = store.build_messages(
        "s",
        "current",
        SystemMessage("system"),
        lambda items: sum(len(str(message.content)) for message in items),
    )

    assert [message.content for message in messages] == ["system", "current"]


def test_build_messages_does_not_mutate_committed_history() -> None:
    """Catch context construction that discards history while applying a budget."""
    store = SessionStore(token_budget=20)
    store.commit("s", "previous user", "previous assistant")

    store.build_messages("s", "first current", SystemMessage("system"), lambda _: 100)
    messages = store.build_messages(
        "s", "second current", SystemMessage("system"), lambda _: 0
    )

    assert [message.content for message in messages] == [
        "system",
        "previous user",
        "previous assistant",
        "second current",
    ]
