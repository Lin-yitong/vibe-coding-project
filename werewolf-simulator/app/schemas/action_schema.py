from pydantic import BaseModel


class ActionOutputSchema(BaseModel):
    action: str
    actor_id: str | None = None
    target: str | None = None
    reason: str = ""
