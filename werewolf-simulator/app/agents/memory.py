from pydantic import BaseModel, Field


class AgentMemory(BaseModel):
    notes: dict[str, list[str]] = Field(default_factory=dict)

    def add_note(self, player_id: str, note: str) -> None:
        self.notes.setdefault(player_id, []).append(note)
