from uuid import uuid4


def generate_game_id() -> str:
    return f"game_{uuid4().hex[:12]}"


def generate_player_id(seat_number: int) -> str:
    return f"player_{seat_number}"
