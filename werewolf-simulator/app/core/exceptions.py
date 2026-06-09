class GameError(Exception):
    pass


class GameNotFoundError(GameError):
    pass


class InvalidActionError(GameError):
    pass
