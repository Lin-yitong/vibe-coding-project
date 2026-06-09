from pydantic import BaseModel


class NightAction(BaseModel):
    wolf_target: str | None = None
    seer_target: str | None = None
    witch_save: bool = False
    witch_poison_target: str | None = None


class AgentAction(BaseModel):
    action: str
    actor_id: str | None = None
    target: str | None = None
    reason: str = ""


class WitchAction(BaseModel):
    save: bool = False
    poison_target: str | None = None
    reason: str = ""
