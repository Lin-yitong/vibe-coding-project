import { requestJson } from "./client";
import type { GameState, HealthResponse, LogsResponse, RunResponse, StepResponse } from "../types/game";

export function getHealth() {
  return requestJson<HealthResponse>("/api/health");
}

export function createGame() {
  return requestJson<GameState>("/api/games", { method: "POST" });
}

export function getGame(gameId: string, debug: boolean) {
  return requestJson<GameState>(`/api/games/${gameId}?debug=${debug}`);
}

export function stepGame(gameId: string) {
  return requestJson<StepResponse>(`/api/games/${gameId}/step`, { method: "POST" });
}

export function runGame(gameId: string, maxSteps = 100) {
  return requestJson<RunResponse>(`/api/games/${gameId}/run?max_steps=${maxSteps}`, { method: "POST" });
}

export function getLogs(gameId: string, debug: boolean) {
  return requestJson<LogsResponse>(`/api/games/${gameId}/logs?debug=${debug}`);
}

export function deleteGame(gameId: string) {
  return requestJson<void>(`/api/games/${gameId}`, { method: "DELETE" });
}
