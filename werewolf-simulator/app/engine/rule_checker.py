from app.models.game import GameState
from app.models.role import Role


class RuleChecker:
    def is_alive(self, game: GameState, player_id: str | None) -> bool:
        if player_id is None:
            return False
        player = game.get_player(player_id)
        return bool(player and player.is_alive)

    def legal_wolf_targets(self, game: GameState) -> list[str]:
        return [player.player_id for player in game.alive_players() if player.role != Role.WEREWOLF]

    def legal_seer_targets(self, game: GameState) -> list[str]:
        return [player.player_id for player in game.alive_players()]

    def legal_vote_targets(self, game: GameState) -> list[str]:
        return [player.player_id for player in game.alive_players()]

    def legal_poison_targets(self, game: GameState) -> list[str]:
        if not game.witch_poison_available:
            return []
        return [player.player_id for player in game.alive_players()]

    def can_wolf_kill(self, game: GameState, target_id: str | None) -> bool:
        return target_id in self.legal_wolf_targets(game)

    def can_seer_check(self, game: GameState, target_id: str | None) -> bool:
        return target_id in self.legal_seer_targets(game)

    def can_witch_save(self, game: GameState, save: bool) -> bool:
        return (not save) or (game.witch_antidote_available and game.night_action.wolf_target is not None)

    def can_witch_poison(self, game: GameState, target_id: str | None) -> bool:
        if target_id is None:
            return True
        return target_id in self.legal_poison_targets(game)

    def can_vote(self, game: GameState, voter_id: str | None, target_id: str | None) -> bool:
        return self.is_alive(game, voter_id) and target_id in self.legal_vote_targets(game)

    def can_speak(self, game: GameState, player_id: str | None) -> bool:
        return self.is_alive(game, player_id)
