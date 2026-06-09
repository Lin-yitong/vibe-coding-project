import random

from app.core.config import settings
from app.engine.game_engine import GameEngine
from app.engine.rule_checker import RuleChecker
from app.models.action import NightAction
from app.models.game import GameState
from app.models.player import Player
from app.models.role import GamePhase, Role
from app.repositories.game_repository import GameRepository, game_repository
from app.services.agent_service import AgentService
from app.services.log_service import LogService
from app.utils.id_generator import generate_game_id, generate_player_id


class GameService:
    def __init__(
        self,
        repository: GameRepository | None = None,
        engine: GameEngine | None = None,
        agent_service: AgentService | None = None,
        log_service: LogService | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.repository = repository or game_repository
        self.rule_checker = RuleChecker()
        self.engine = engine or GameEngine(rule_checker=self.rule_checker)
        self.agent_service = agent_service or AgentService(rule_checker=self.rule_checker)
        self.log_service = log_service or LogService()
        self.rng = rng or random.Random()

    def create_game(self) -> GameState:
        roles = [Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.WITCH, Role.VILLAGER, Role.VILLAGER]
        self.rng.shuffle(roles)
        players = [
            Player(
                player_id=generate_player_id(seat_number),
                nickname=f"{seat_number}号玩家",
                role=roles[seat_number - 1],
                seat_number=seat_number,
                is_ai=True,
            )
            for seat_number in range(1, 7)
        ]
        game = GameState(game_id=generate_game_id(), players=players)
        self.log_service.public(game, "游戏创建完成，6 名玩家入座。")
        self.log_service.public(game, "第 1 夜开始。")
        self.log_service.debug(game, f"Roles: {[(player.seat_number, player.role.value) for player in players]}")
        return self.repository.save(game)

    def get_game(self, game_id: str) -> GameState:
        return self.repository.get(game_id)

    def delete_game(self, game_id: str) -> None:
        self.repository.delete(game_id)

    def step_game(self, game_id: str) -> tuple[GameState, list[str]]:
        game = self.repository.get(game_id)
        before_count = len(game.public_logs)

        if game.phase == GamePhase.GAME_OVER:
            return game, []

        if game.phase == GamePhase.NIGHT_WOLF:
            self._night_wolf(game)
        elif game.phase == GamePhase.NIGHT_SEER:
            self._night_seer(game)
        elif game.phase == GamePhase.NIGHT_WITCH:
            self._night_witch(game)
        elif game.phase == GamePhase.DAY_ANNOUNCEMENT:
            self._day_announcement(game)
        elif game.phase == GamePhase.DAY_SPEECH:
            self._day_speech(game)
        elif game.phase == GamePhase.DAY_VOTE:
            self._day_vote(game)
        elif game.phase == GamePhase.EXILE:
            self._exile(game)

        self.repository.save(game)
        return game, game.public_logs[before_count:]

    def run_game(self, game_id: str, max_steps: int | None = None) -> GameState:
        limit = max_steps or settings.max_run_steps
        game = self.repository.get(game_id)
        for _ in range(limit):
            if game.phase == GamePhase.GAME_OVER:
                break
            game, _ = self.step_game(game_id)
        if game.phase != GamePhase.GAME_OVER:
            game.debug_logs.append(f"Run stopped after {limit} steps without a winner.")
        return game

    def _night_wolf(self, game: GameState) -> None:
        action = self.agent_service.choose_wolf_target(game)
        if action.target:
            self.engine.apply_wolf_target(game, action.target)
            self.log_service.public(game, f"第 {game.day_number} 夜，夜间行动已记录。")
        self.engine.advance_phase(game)

    def _night_seer(self, game: GameState) -> None:
        action = self.agent_service.choose_seer_target(game)
        if action and action.target:
            self.engine.apply_seer_target(game, action.target)
            self.log_service.public(game, f"第 {game.day_number} 夜，夜间行动已记录。")
        self.engine.advance_phase(game)

    def _night_witch(self, game: GameState) -> None:
        action = self.agent_service.choose_witch_action(game)
        if action:
            self.engine.apply_witch_action(game, action.save, action.poison_target)
            self.log_service.public(game, f"第 {game.day_number} 夜，夜间行动已记录。")
        self.engine.settle_night(game)
        self.engine.check_winner(game)
        if game.phase != GamePhase.GAME_OVER:
            self.engine.advance_phase(game)

    def _day_announcement(self, game: GameState) -> None:
        if game.pending_night_deaths:
            seats = self._seat_text(game, game.pending_night_deaths)
            self.log_service.public(game, f"第 {game.day_number} 天公布昨夜死亡：{seats}。")
        else:
            self.log_service.public(game, f"第 {game.day_number} 天公布昨夜平安夜。")
        self.engine.check_winner(game)
        if game.phase != GamePhase.GAME_OVER:
            self.engine.advance_phase(game)

    def _day_speech(self, game: GameState) -> None:
        speakers = sorted(game.alive_players(), key=lambda player: player.seat_number)
        next_speaker = next((player for player in speakers if player.player_id not in game.speeches), None)
        if not next_speaker:
            game.speech_cursor = 0
            self.engine.advance_phase(game)
            return

        speech = self.agent_service.generate_speech(game, next_speaker)
        if speech:
            game.speeches[next_speaker.player_id] = speech
            game.speech_cursor = len(game.speeches)
            self.log_service.public(
                game,
                f"第 {game.day_number} 天发言 - {next_speaker.seat_number} 号玩家：{speech}",
            )

        if len(game.speeches) >= len(speakers):
            game.speech_cursor = 0
            self.engine.advance_phase(game)

    def _day_vote(self, game: GameState) -> None:
        game.votes.clear()
        for player in game.alive_players():
            action = self.agent_service.vote(game, player)
            if action and action.target:
                self.engine.record_vote(game, player.player_id, action.target)
        self.log_service.public(game, f"第 {game.day_number} 天投票完成。")
        self.engine.advance_phase(game)

    def _exile(self, game: GameState) -> None:
        self.engine.settle_vote(game)
        self.engine.finish_day_or_continue(game)
        if game.phase == GamePhase.GAME_OVER and game.winner:
            self.log_service.public(game, f"游戏结束，{game.winner.value} 阵营胜利。")
        elif game.phase == GamePhase.NIGHT_WOLF:
            self.log_service.public(game, f"第 {game.day_number} 夜开始。")

    def _seat_text(self, game: GameState, player_ids: list[str]) -> str:
        seats = []
        for player_id in player_ids:
            player = game.get_player(player_id)
            if player:
                seats.append(f"{player.seat_number} 号玩家")
        return "、".join(seats)


game_service = GameService()
