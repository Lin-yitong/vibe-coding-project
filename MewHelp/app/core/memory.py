from collections.abc import Callable, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class SessionStore:
    def __init__(self, token_budget: int = 2000) -> None:
        self.token_budget = token_budget
        self._history: dict[str, list[tuple[str, str]]] = {}

    def build_messages(
        self,
        session_id: str,
        current_message: str,
        system_message: BaseMessage,
        count_tokens: Callable[[Sequence[BaseMessage]], int],
    ) -> list[BaseMessage]:
        selected_pairs: list[tuple[str, str]] = []
        for pair in reversed(self._history.get(session_id, [])):
            candidate_pairs = [pair, *selected_pairs]
            candidate = self._compose_messages(
                system_message, candidate_pairs, current_message
            )
            if count_tokens(candidate) <= self.token_budget:
                selected_pairs = candidate_pairs
            else:
                break

        return self._compose_messages(system_message, selected_pairs, current_message)

    def commit(self, session_id: str, user_message: str, assistant_message: str) -> None:
        self._history.setdefault(session_id, []).append((user_message, assistant_message))

    @staticmethod
    def _compose_messages(
        system_message: BaseMessage,
        pairs: Sequence[tuple[str, str]],
        current_message: str,
    ) -> list[BaseMessage]:
        messages: list[BaseMessage] = [system_message]
        for user_message, assistant_message in pairs:
            messages.extend(
                [HumanMessage(content=user_message), AIMessage(content=assistant_message)]
            )
        messages.append(HumanMessage(content=current_message))
        return messages
