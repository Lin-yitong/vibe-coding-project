from collections import Counter

from app.engine.phase_manager import PhaseManager
from app.engine.rule_checker import RuleChecker
from app.models.game import GameState
from app.models.role import GamePhase, Role, Winner


class GameEngine:
    def __init__(self, rule_checker: RuleChecker | None = None, phase_manager: PhaseManager | None = None) -> None:
        self.rule_checker = rule_checker or RuleChecker()
        self.phase_manager = phase_manager or PhaseManager()

    def apply_wolf_target(self, game: GameState, target_id: str) -> None:
        game.night_action.wolf_target = target_id
        game.debug_logs.append(f"第 {game.day_number} 夜狼人行动：选择击杀 {self._player_label(game, target_id)}。")

    def apply_seer_target(self, game: GameState, target_id: str) -> None:
        target = game.get_player(target_id)
        game.night_action.seer_target = target_id
        if target:
            result = "狼人" if target.role == Role.WEREWOLF else "好人"
            game.debug_logs.append(
                f"第 {game.day_number} 夜预言家行动：查验 {self._player_label(game, target_id)}，结果为 {result}。"
            )

    def apply_witch_action(self, game: GameState, save: bool, poison_target: str | None) -> None:
        game.night_action.witch_save = save
        game.night_action.witch_poison_target = poison_target
        wolf_target = game.night_action.wolf_target
        if save:
            game.witch_antidote_available = False
            game.debug_logs.append(
                f"第 {game.day_number} 夜女巫行动：使用解药，救下 {self._player_label(game, wolf_target)}。"
            )
        else:
            game.debug_logs.append(f"第 {game.day_number} 夜女巫行动：未使用解药。")
        if poison_target:
            game.witch_poison_available = False
            game.debug_logs.append(f"第 {game.day_number} 夜女巫行动：使用毒药，毒杀 {self._player_label(game, poison_target)}。")
        else:
            game.debug_logs.append(f"第 {game.day_number} 夜女巫行动：未使用毒药。")

    def settle_night(self, game: GameState) -> list[str]:
        deaths: list[str] = []
        wolf_target = game.night_action.wolf_target
        if wolf_target and not game.night_action.witch_save:
            deaths.append(wolf_target)
        poison_target = game.night_action.witch_poison_target
        if poison_target and poison_target not in deaths:
            deaths.append(poison_target)

        for player_id in deaths:
            player = game.get_player(player_id)
            if player and player.is_alive:
                player.is_alive = False

        game.pending_night_deaths = deaths
        if deaths:
            dead_text = "、".join(self._player_label(game, player_id) for player_id in deaths)
            game.debug_logs.append(f"第 {game.day_number} 夜结算：死亡玩家为 {dead_text}。")
        else:
            game.debug_logs.append(f"第 {game.day_number} 夜结算：平安夜，无人死亡。")
        return deaths

    def record_vote(self, game: GameState, voter_id: str, target_id: str) -> None:
        game.votes[voter_id] = target_id

    def settle_vote(self, game: GameState) -> str | None:
        if not game.votes:
            game.pending_exile = None
            return None

        counts = Counter(game.votes.values())
        top_count = max(counts.values())
        top_targets = sorted(target for target, count in counts.items() if count == top_count)
        if len(top_targets) != 1:
            game.pending_exile = None
            game.public_logs.append(f"第 {game.day_number} 天投票平票，无人出局。")
            return None

        exiled_id = top_targets[0]
        player = game.get_player(exiled_id)
        if player and player.is_alive:
            player.is_alive = False
            game.pending_exile = exiled_id
            game.public_logs.append(f"第 {game.day_number} 天，{player.seat_number} 号玩家被放逐。")
            return exiled_id

        game.pending_exile = None
        return None

    def check_winner(self, game: GameState) -> Winner | None:
        alive = game.alive_players()
        wolves = [player for player in alive if player.role == Role.WEREWOLF]
        good = [player for player in alive if player.role != Role.WEREWOLF]

        if not wolves:
            game.winner = Winner.GOOD
            game.phase = GamePhase.GAME_OVER
        elif len(wolves) >= len(good):
            game.winner = Winner.WEREWOLF
            game.phase = GamePhase.GAME_OVER
        return game.winner

    def finish_day_or_continue(self, game: GameState) -> None:
        if self.check_winner(game):
            return
        game.day_number += 1
        game.phase = GamePhase.NIGHT_WOLF
        game.night_action.wolf_target = None
        game.night_action.seer_target = None
        game.night_action.witch_save = False
        game.night_action.witch_poison_target = None
        game.votes.clear()
        game.speeches.clear()
        game.speech_cursor = 0
        game.pending_night_deaths.clear()
        game.pending_exile = None

    def advance_phase(self, game: GameState) -> None:
        if game.phase != GamePhase.GAME_OVER:
            game.phase = self.phase_manager.next_after(game.phase)

    def _player_label(self, game: GameState, player_id: str | None) -> str:
        if player_id is None:
            return "无目标"
        player = game.get_player(player_id)
        if not player:
            return player_id
        return f"{player.seat_number} 号玩家({player.player_id}, {player.role.value})"
