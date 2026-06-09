from app.core.exceptions import GameNotFoundError
from app.models.game import GameState


class GameRepository:
    def __init__(self) -> None:
        self._games: dict[str, GameState] = {}

    def save(self, game: GameState) -> GameState:
        self._games[game.game_id] = game
        return game

    def get(self, game_id: str) -> GameState:
        try:
            return self._games[game_id]
        except KeyError as exc:
            raise GameNotFoundError(f"Game not found: {game_id}") from exc

    def delete(self, game_id: str) -> None:
        if game_id not in self._games:
            raise GameNotFoundError(f"Game not found: {game_id}")
        del self._games[game_id]

    def clear(self) -> None:
        self._games.clear()


game_repository = GameRepository()
