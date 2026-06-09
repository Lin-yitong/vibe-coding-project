from pydantic import BaseModel, Field

from app.models.role import Role


class Player(BaseModel):
    player_id: str
    nickname: str
    role: Role
    is_alive: bool = True
    seat_number: int = Field(ge=1, le=6)
    is_ai: bool = True
