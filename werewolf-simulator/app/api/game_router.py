from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings
from app.core.exceptions import GameNotFoundError
from app.models.role import GamePhase
from app.schemas.game_schema import (
    GameStateSchema,
    LogsResponseSchema,
    RunResponseSchema,
    StepResponseSchema,
    to_game_schema,
)
from app.services.game_service import game_service


router = APIRouter(prefix="/api/games", tags=["games"])


@router.post("", response_model=GameStateSchema, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
def create_game() -> GameStateSchema:
    game = game_service.create_game()
    return to_game_schema(game, debug=False)


@router.get("/{game_id}", response_model=GameStateSchema, response_model_exclude_none=True)
def get_game(game_id: str, debug: bool = Query(False)) -> GameStateSchema:
    try:
        game = game_service.get_game(game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return to_game_schema(game, debug=debug)


@router.post("/{game_id}/step", response_model=StepResponseSchema)
def step_game(game_id: str) -> StepResponseSchema:
    try:
        game, new_logs = game_service.step_game(game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return StepResponseSchema(
        game_id=game.game_id,
        phase=game.phase,
        new_public_logs=new_logs,
        is_over=game.phase == GamePhase.GAME_OVER,
        winner=game.winner,
    )


@router.post("/{game_id}/run", response_model=RunResponseSchema)
def run_game(game_id: str, max_steps: int = Query(settings.max_run_steps, ge=1, le=1000)) -> RunResponseSchema:
    try:
        game = game_service.run_game(game_id, max_steps=max_steps)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RunResponseSchema(game_id=game.game_id, winner=game.winner, public_logs=game.public_logs)


@router.get("/{game_id}/logs", response_model=LogsResponseSchema, response_model_exclude_none=True)
def get_logs(game_id: str, debug: bool = Query(False)) -> LogsResponseSchema:
    try:
        game = game_service.get_game(game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LogsResponseSchema(public_logs=game.public_logs, debug_logs=game.debug_logs if debug else None)


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game(game_id: str) -> None:
    try:
        game_service.delete_game(game_id)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
