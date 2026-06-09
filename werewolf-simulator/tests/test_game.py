from collections import Counter

from fastapi.testclient import TestClient

from app.engine.game_engine import GameEngine
from app.engine.rule_checker import RuleChecker
from app.main import app
from app.models.action import NightAction
from app.models.game import GameState
from app.models.player import Player
from app.models.role import GamePhase, Role, Winner
from app.repositories.game_repository import GameRepository, game_repository
from app.services.agent_service import AgentService
from app.services.game_service import GameService
from app.agents.random_agent import RandomAgent


client = TestClient(app)


def setup_function() -> None:
    game_repository.clear()


def make_game(players: list[Player]) -> GameState:
    return GameState(game_id="test_game", players=players)


def player(seat: int, role: Role, alive: bool = True) -> Player:
    return Player(
        player_id=f"player_{seat}",
        nickname=f"{seat}号玩家",
        role=role,
        is_alive=alive,
        seat_number=seat,
    )


def test_create_game() -> None:
    response = client.post("/api/games")

    assert response.status_code == 201
    data = response.json()
    assert len(data["players"]) == 6
    assert all("role" not in item for item in data["players"])

    debug_response = client.get(f"/api/games/{data['game_id']}?debug=true")
    roles = Counter(item["role"] for item in debug_response.json()["players"])
    assert roles["WEREWOLF"] == 2
    assert roles["SEER"] == 1
    assert roles["WITCH"] == 1
    assert roles["VILLAGER"] == 2


def test_step_game() -> None:
    created = client.post("/api/games").json()
    response = client.post(f"/api/games/{created['game_id']}/step")

    assert response.status_code == 200
    assert response.json()["phase"] != created["phase"]


def test_run_game() -> None:
    created = client.post("/api/games").json()
    response = client.post(f"/api/games/{created['game_id']}/run")

    assert response.status_code == 200
    assert response.json()["winner"] in {"GOOD", "WEREWOLF"}


def test_winner_good() -> None:
    game = make_game(
        [
            player(1, Role.WEREWOLF, alive=False),
            player(2, Role.WEREWOLF, alive=False),
            player(3, Role.SEER),
            player(4, Role.WITCH),
            player(5, Role.VILLAGER),
            player(6, Role.VILLAGER),
        ]
    )

    winner = GameEngine().check_winner(game)

    assert winner == Winner.GOOD
    assert game.phase == GamePhase.GAME_OVER


def test_winner_wolf() -> None:
    game = make_game(
        [
            player(1, Role.WEREWOLF),
            player(2, Role.WEREWOLF),
            player(3, Role.SEER, alive=False),
            player(4, Role.WITCH, alive=False),
            player(5, Role.VILLAGER),
            player(6, Role.VILLAGER),
        ]
    )

    winner = GameEngine().check_winner(game)

    assert winner == Winner.WEREWOLF
    assert game.phase == GamePhase.GAME_OVER


def test_dead_player_cannot_vote() -> None:
    game = make_game(
        [
            player(1, Role.WEREWOLF, alive=False),
            player(2, Role.WEREWOLF),
            player(3, Role.SEER),
            player(4, Role.WITCH),
            player(5, Role.VILLAGER),
            player(6, Role.VILLAGER),
        ]
    )

    assert not RuleChecker().can_vote(game, "player_1", "player_3")
    assert RuleChecker().can_vote(game, "player_2", "player_3")


def test_witch_medicine_once() -> None:
    game = make_game(
        [
            player(1, Role.WEREWOLF),
            player(2, Role.WEREWOLF),
            player(3, Role.SEER),
            player(4, Role.WITCH),
            player(5, Role.VILLAGER),
            player(6, Role.VILLAGER),
        ]
    )
    game.night_action = NightAction(wolf_target="player_5")
    engine = GameEngine()

    assert RuleChecker().can_witch_save(game, True)
    assert RuleChecker().can_witch_poison(game, "player_6")

    engine.apply_witch_action(game, save=True, poison_target="player_6")

    assert not game.witch_antidote_available
    assert not game.witch_poison_available
    assert not RuleChecker().can_witch_save(game, True)
    assert not RuleChecker().can_witch_poison(game, "player_3")


def test_public_response_does_not_leak_roles() -> None:
    created = client.post("/api/games").json()
    public_response = client.get(f"/api/games/{created['game_id']}")
    debug_response = client.get(f"/api/games/{created['game_id']}?debug=true")

    assert all("role" not in item for item in public_response.json()["players"])
    assert any(item["role"] == "WEREWOLF" for item in debug_response.json()["players"])
    assert "debug_logs" not in public_response.json()
    assert isinstance(debug_response.json()["debug_logs"], list)


def test_day_speech_steps_one_player_at_a_time() -> None:
    repository = GameRepository()
    agent_service = AgentService(agent=RandomAgent())
    service = GameService(repository=repository, agent_service=agent_service)
    game = make_game(
        [
            player(1, Role.WEREWOLF),
            player(2, Role.WEREWOLF),
            player(3, Role.SEER),
            player(4, Role.WITCH),
            player(5, Role.VILLAGER),
            player(6, Role.VILLAGER),
        ]
    )
    game.phase = GamePhase.DAY_SPEECH
    repository.save(game)

    game, new_logs = service.step_game(game.game_id)

    assert game.phase == GamePhase.DAY_SPEECH
    assert len(game.speeches) == 1
    assert len(new_logs) == 1
    assert "1 号玩家" in new_logs[0]


def test_night_actions_are_visible_in_debug_logs_only() -> None:
    game = make_game(
        [
            player(1, Role.WEREWOLF),
            player(2, Role.WEREWOLF),
            player(3, Role.SEER),
            player(4, Role.WITCH),
            player(5, Role.VILLAGER),
            player(6, Role.VILLAGER),
        ]
    )
    engine = GameEngine()

    engine.apply_wolf_target(game, "player_5")
    engine.apply_seer_target(game, "player_1")
    engine.apply_witch_action(game, save=False, poison_target="player_6")
    engine.settle_night(game)

    debug_text = "\n".join(game.debug_logs)
    public_text = "\n".join(game.public_logs)
    assert "狼人行动" in debug_text
    assert "预言家行动" in debug_text
    assert "结果为 狼人" in debug_text
    assert "女巫行动" in debug_text
    assert "毒杀 6 号玩家" in debug_text
    assert "WEREWOLF" not in public_text
