from pydantic import BaseModel, Field

from app.models.action import NightAction
from app.models.player import Player
from app.models.role import GamePhase, Winner


class GameState(BaseModel):
    game_id: str
    day_number: int = 1
    phase: GamePhase = GamePhase.NIGHT_WOLF
    players: list[Player]
    night_action: NightAction = Field(default_factory=NightAction)
    votes: dict[str, str] = Field(default_factory=dict)
    speeches: dict[str, str] = Field(default_factory=dict)
    speech_cursor: int = 0
    public_logs: list[str] = Field(default_factory=list)
    debug_logs: list[str] = Field(default_factory=list)
    winner: Winner | None = None
    witch_antidote_available: bool = True
    witch_poison_available: bool = True
    pending_night_deaths: list[str] = Field(default_factory=list)
    pending_exile: str | None = None

    def get_player(self, player_id: str) -> Player | None:
        return next((player for player in self.players if player.player_id == player_id), None)

    def alive_players(self) -> list[Player]:
        return [player for player in self.players if player.is_alive]
