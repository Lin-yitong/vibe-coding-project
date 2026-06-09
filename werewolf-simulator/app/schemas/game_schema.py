from pydantic import BaseModel

from app.models.game import GameState
from app.models.role import GamePhase, Role, Winner


class PlayerPublicSchema(BaseModel):
    player_id: str
    nickname: str
    is_alive: bool
    seat_number: int
    is_ai: bool
    role: Role | None = None


class GameStateSchema(BaseModel):
    game_id: str
    day_number: int
    phase: GamePhase
    players: list[PlayerPublicSchema]
    votes: dict[str, str]
    public_logs: list[str]
    debug_logs: list[str] | None = None
    winner: Winner | None


class StepResponseSchema(BaseModel):
    game_id: str
    phase: GamePhase
    new_public_logs: list[str]
    is_over: bool
    winner: Winner | None


class RunResponseSchema(BaseModel):
    game_id: str
    winner: Winner | None
    public_logs: list[str]


class LogsResponseSchema(BaseModel):
    public_logs: list[str]
    debug_logs: list[str] | None = None


def to_game_schema(game: GameState, debug: bool = False) -> GameStateSchema:
    return GameStateSchema(
        game_id=game.game_id,
        day_number=game.day_number,
        phase=game.phase,
        players=[
            PlayerPublicSchema(
                player_id=player.player_id,
                nickname=player.nickname,
                is_alive=player.is_alive,
                seat_number=player.seat_number,
                is_ai=player.is_ai,
                role=player.role if debug else None,
            )
            for player in game.players
        ],
        votes=game.votes,
        public_logs=game.public_logs,
        debug_logs=game.debug_logs if debug else None,
        winner=game.winner,
    )
