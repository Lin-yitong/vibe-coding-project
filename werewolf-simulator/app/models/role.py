from enum import StrEnum


class Role(StrEnum):
    WEREWOLF = "WEREWOLF"
    SEER = "SEER"
    WITCH = "WITCH"
    VILLAGER = "VILLAGER"


class GamePhase(StrEnum):
    NIGHT_WOLF = "NIGHT_WOLF"
    NIGHT_SEER = "NIGHT_SEER"
    NIGHT_WITCH = "NIGHT_WITCH"
    DAY_ANNOUNCEMENT = "DAY_ANNOUNCEMENT"
    DAY_SPEECH = "DAY_SPEECH"
    DAY_VOTE = "DAY_VOTE"
    EXILE = "EXILE"
    GAME_OVER = "GAME_OVER"


class Winner(StrEnum):
    GOOD = "GOOD"
    WEREWOLF = "WEREWOLF"
