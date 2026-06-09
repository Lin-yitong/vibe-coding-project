from app.models.game import GameState


class LogService:
    def public(self, game: GameState, message: str) -> None:
        game.public_logs.append(message)

    def debug(self, game: GameState, message: str) -> None:
        game.debug_logs.append(message)
