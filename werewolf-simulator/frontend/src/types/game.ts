export type Role = "WEREWOLF" | "SEER" | "WITCH" | "VILLAGER";

export type GamePhase =
  | "NIGHT_WOLF"
  | "NIGHT_SEER"
  | "NIGHT_WITCH"
  | "DAY_ANNOUNCEMENT"
  | "DAY_SPEECH"
  | "DAY_VOTE"
  | "EXILE"
  | "GAME_OVER";

export type Winner = "GOOD" | "WEREWOLF";

export interface Player {
  player_id: string;
  nickname: string;
  is_alive: boolean;
  seat_number: number;
  is_ai: boolean;
  role?: Role;
}

export interface GameState {
  game_id: string;
  day_number: number;
  phase: GamePhase;
  players: Player[];
  votes: Record<string, string>;
  public_logs: string[];
  debug_logs?: string[];
  winner: Winner | null;
}

export interface StepResponse {
  game_id: string;
  phase: GamePhase;
  new_public_logs: string[];
  is_over: boolean;
  winner: Winner | null;
}

export interface RunResponse {
  game_id: string;
  winner: Winner | null;
  public_logs: string[];
}

export interface LogsResponse {
  public_logs: string[];
  debug_logs?: string[];
}

export interface HealthResponse {
  status: string;
}
