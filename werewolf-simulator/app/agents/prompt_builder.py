from app.models.game import GameState
from app.models.player import Player
from app.models.role import Role


class PromptBuilder:
    def system_prompt(self) -> str:
        return (
            "You are an automated player in a 6-player Werewolf game. "
            "Return only valid JSON. Do not include markdown or extra text. "
            "Use only the information provided in the prompt. Never assume hidden roles."
        )

    def build_action_prompt(
        self,
        game: GameState,
        player: Player,
        task: str,
        legal_targets: list[str],
        extra_context: str = "",
    ) -> str:
        return "\n".join(
            [
                self._base_context(game, player),
                self._role_context(game, player),
                f"Task: {task}",
                f"Legal target player_ids: {legal_targets}",
                extra_context,
                'Return JSON like {"action":"vote","target":"player_3","reason":"short reason"}.',
            ]
        ).strip()

    def build_witch_prompt(self, game: GameState, witch: Player, legal_poison_targets: list[str]) -> str:
        attacked = game.night_action.wolf_target
        return "\n".join(
            [
                self._base_context(game, witch),
                self._role_context(game, witch),
                f"Wolf attack target this night: {attacked}",
                f"Antidote available: {game.witch_antidote_available}",
                f"Poison available: {game.witch_poison_available}",
                f"Legal poison target player_ids: {legal_poison_targets}",
                (
                    'Return JSON like {"save":true,"poison_target":null,"reason":"short reason"}. '
                    "poison_target must be null or one legal player_id."
                ),
            ]
        ).strip()

    def build_speech_prompt(self, game: GameState, player: Player) -> str:
        return "\n".join(
            [
                self._base_context(game, player),
                self._role_context(game, player),
                "Task: Make a short public daytime speech without revealing hidden information you should not reveal.",
                'Return JSON like {"speech":"your public speech"}.',
            ]
        ).strip()

    def _base_context(self, game: GameState, player: Player) -> str:
        alive = [
            {"player_id": p.player_id, "seat_number": p.seat_number, "nickname": p.nickname}
            for p in game.alive_players()
        ]
        logs = game.public_logs[-20:]
        return (
            f"You are player_id={player.player_id}, seat_number={player.seat_number}. "
            f"Your role is {player.role.value}. Current day={game.day_number}, phase={game.phase.value}.\n"
            f"Alive players: {alive}\n"
            f"Public logs: {logs}"
        )

    def _role_context(self, game: GameState, player: Player) -> str:
        if player.role == Role.WEREWOLF:
            wolves = [
                {"player_id": p.player_id, "seat_number": p.seat_number}
                for p in game.players
                if p.role == Role.WEREWOLF
            ]
            return f"Werewolf-only info: your wolf teammates are {wolves}."
        if player.role == Role.SEER:
            return "Seer-only info: you may choose one alive player to check tonight."
        if player.role == Role.WITCH:
            return "Witch-only info: you may use each medicine at most once."
        return "Villager info: you have no hidden role information."
