from app.models.role import GamePhase


class PhaseManager:
    _next_phase = {
        GamePhase.NIGHT_WOLF: GamePhase.NIGHT_SEER,
        GamePhase.NIGHT_SEER: GamePhase.NIGHT_WITCH,
        GamePhase.NIGHT_WITCH: GamePhase.DAY_ANNOUNCEMENT,
        GamePhase.DAY_ANNOUNCEMENT: GamePhase.DAY_SPEECH,
        GamePhase.DAY_SPEECH: GamePhase.DAY_VOTE,
        GamePhase.DAY_VOTE: GamePhase.EXILE,
        GamePhase.EXILE: GamePhase.NIGHT_WOLF,
    }

    def next_after(self, phase: GamePhase) -> GamePhase:
        return self._next_phase.get(phase, GamePhase.GAME_OVER)
