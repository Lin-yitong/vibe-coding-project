from app.agents.llm_player import LLMPlayer
from app.agents.random_agent import RandomAgent
from app.core.config import settings
from app.engine.rule_checker import RuleChecker
from app.models.action import AgentAction, WitchAction
from app.models.game import GameState
from app.models.player import Player
from app.models.role import Role


class AgentService:
    def __init__(self, agent: RandomAgent | None = None, rule_checker: RuleChecker | None = None) -> None:
        self.rule_checker = rule_checker or RuleChecker()
        self.agent = agent or self._build_default_agent()

    def choose_wolf_target(self, game: GameState) -> AgentAction:
        wolves = [player for player in game.alive_players() if player.role == Role.WEREWOLF]
        action = self.agent.choose_wolf_target(game, wolves)
        if self.rule_checker.can_wolf_kill(game, action.target):
            return action
        fallback = self._first(self.rule_checker.legal_wolf_targets(game))
        game.debug_logs.append(f"Illegal wolf action {action.model_dump()}; fallback target={fallback}.")
        return AgentAction(action="kill", actor_id=wolves[0].player_id if wolves else None, target=fallback, reason="fallback")

    def choose_seer_target(self, game: GameState) -> AgentAction | None:
        seer = self._alive_role(game, Role.SEER)
        if not seer:
            return None
        action = self.agent.choose_seer_target(game, seer)
        if self.rule_checker.can_seer_check(game, action.target):
            return action
        fallback = self._first([pid for pid in self.rule_checker.legal_seer_targets(game) if pid != seer.player_id])
        game.debug_logs.append(f"Illegal seer action {action.model_dump()}; fallback target={fallback}.")
        return AgentAction(action="check", actor_id=seer.player_id, target=fallback, reason="fallback")

    def choose_witch_action(self, game: GameState) -> WitchAction | None:
        witch = self._alive_role(game, Role.WITCH)
        if not witch:
            return None
        action = self.agent.choose_witch_action(game, witch)
        save = action.save if self.rule_checker.can_witch_save(game, action.save) else False
        poison_target = action.poison_target if self.rule_checker.can_witch_poison(game, action.poison_target) else None
        if save != action.save or poison_target != action.poison_target:
            game.debug_logs.append(f"Illegal witch action {action.model_dump()}; fallback save={save}, poison={poison_target}.")
        return WitchAction(save=save, poison_target=poison_target, reason=action.reason)

    def generate_speech(self, game: GameState, player: Player) -> str:
        if not self.rule_checker.can_speak(game, player.player_id):
            game.debug_logs.append(f"Dead player tried to speak: {player.player_id}.")
            return ""
        return self.agent.generate_speech(game, player)

    def vote(self, game: GameState, player: Player) -> AgentAction | None:
        if not player.is_alive:
            game.debug_logs.append(f"Dead player tried to vote: {player.player_id}.")
            return None
        action = self.agent.vote(game, player)
        if self.rule_checker.can_vote(game, action.actor_id, action.target):
            return action
        fallback = self._first([pid for pid in self.rule_checker.legal_vote_targets(game) if pid != player.player_id])
        game.debug_logs.append(f"Illegal vote action {action.model_dump()}; fallback target={fallback}.")
        if fallback is None:
            return None
        return AgentAction(action="vote", actor_id=player.player_id, target=fallback, reason="fallback")

    def _alive_role(self, game: GameState, role: Role) -> Player | None:
        return next((player for player in game.alive_players() if player.role == role), None)

    def _first(self, values: list[str]) -> str | None:
        return values[0] if values else None

    def _build_default_agent(self) -> RandomAgent:
        if settings.llm_enabled:
            return LLMPlayer(rule_checker=self.rule_checker)
        return RandomAgent(rule_checker=self.rule_checker)
