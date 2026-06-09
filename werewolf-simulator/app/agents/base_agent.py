from abc import ABC, abstractmethod

from app.models.action import AgentAction, WitchAction
from app.models.game import GameState
from app.models.player import Player


class BaseAgent(ABC):
    @abstractmethod
    def choose_wolf_target(self, game: GameState, wolves: list[Player]) -> AgentAction:
        raise NotImplementedError

    @abstractmethod
    def choose_seer_target(self, game: GameState, seer: Player) -> AgentAction:
        raise NotImplementedError

    @abstractmethod
    def choose_witch_action(self, game: GameState, witch: Player) -> WitchAction:
        raise NotImplementedError

    @abstractmethod
    def generate_speech(self, game: GameState, player: Player) -> str:
        raise NotImplementedError

    @abstractmethod
    def vote(self, game: GameState, player: Player) -> AgentAction:
        raise NotImplementedError
