import random

from app.agents.base_agent import BaseAgent
from app.engine.rule_checker import RuleChecker
from app.models.action import AgentAction, WitchAction
from app.models.game import GameState
from app.models.player import Player


class RandomAgent(BaseAgent):
    def __init__(self, rng: random.Random | None = None, rule_checker: RuleChecker | None = None) -> None:
        self.rng = rng or random.Random()
        self.rule_checker = rule_checker or RuleChecker()

    def choose_wolf_target(self, game: GameState, wolves: list[Player]) -> AgentAction:
        targets = self.rule_checker.legal_wolf_targets(game)
        target = self.rng.choice(targets) if targets else None
        actor_id = wolves[0].player_id if wolves else None
        return AgentAction(action="kill", actor_id=actor_id, target=target, reason="RandomAgent selected a wolf target.")

    def choose_seer_target(self, game: GameState, seer: Player) -> AgentAction:
        targets = [target for target in self.rule_checker.legal_seer_targets(game) if target != seer.player_id]
        target = self.rng.choice(targets) if targets else None
        return AgentAction(action="check", actor_id=seer.player_id, target=target, reason="RandomAgent selected a seer target.")

    def choose_witch_action(self, game: GameState, witch: Player) -> WitchAction:
        save = bool(game.night_action.wolf_target and game.witch_antidote_available and self.rng.choice([True, False]))
        poison_target = None
        if game.witch_poison_available and self.rng.choice([True, False]):
            targets = [target for target in self.rule_checker.legal_poison_targets(game) if target != witch.player_id]
            poison_target = self.rng.choice(targets) if targets else None
        return WitchAction(save=save, poison_target=poison_target, reason="RandomAgent selected witch action.")

    def generate_speech(self, game: GameState, player: Player) -> str:
        return "我会根据目前公开信息谨慎投票。"

    def vote(self, game: GameState, player: Player) -> AgentAction:
        targets = [target for target in self.rule_checker.legal_vote_targets(game) if target != player.player_id]
        target = self.rng.choice(targets) if targets else None
        return AgentAction(action="vote", actor_id=player.player_id, target=target, reason="RandomAgent selected a vote target.")
