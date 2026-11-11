export type Direction = 'up' | 'down' | 'left' | 'right'
export type GameStatus = 'playing' | 'paused' | 'won' | 'game_over'
export type GameMode = 'manual' | 'jev'
export type Strategy = 'basic' | 'strategic'

export interface MoveAnalysis {
  board_after: number[][]
  empty_cells_after: number
  merge_count: number
  score_gain: number
  max_tile_after: number
  max_tile_positions: [number, number][]
  tile_count_after: number
  empty_rows_after: number
  empty_columns_after: number
  max_tile_in_corner: boolean
}

export interface Decision {
  move: Direction
  origin: 'jev' | 'forced'
  probabilities: Partial<Record<Direction, number>>
  confidence: number | null
  latency_ms: number | null
  model: string
  input_tokens: number | null
  output_tokens: number | null
  strategy: Strategy
  legal_move_count: number
  request_bytes: number
  move_analysis: Partial<Record<Direction, MoveAnalysis>>
}

export interface HistoryEntry {
  number: number
  move: Direction
  score: number
  score_gained: number
  origin: 'jev' | 'forced' | 'manual'
  latency_ms: number | null
  confidence: number | null
  created_at: string
}

export interface GameState {
  id: string
  board: number[][]
  score: number
  best_score: number
  highest_tile: number
  empty_cells: number
  total_moves: number
  status: GameStatus
  mode: GameMode
  strategy: Strategy
  seed: number
  won_once: boolean
  generation: number
  state_version: number
  decision_pending: boolean
  elapsed_seconds: number
  last_error: string | null
  spawned_at: [number, number] | null
  merged_positions: [number, number][]
  last_direction: Direction | null
  decision: Decision | null
  history: HistoryEntry[]
  metrics: {
    total_jev_calls: number
    successful_moves: number
    api_errors: number
    average_latency_ms: number
    total_input_tokens: number
    total_output_tokens: number
    average_request_bytes: number | null
  }
  strategy_transitions: { from: Strategy; to: Strategy; move_number: number; changed_at: string }[]
}

export interface StrategyStats {
  games: number
  completed_games: number
  average_score: number
  max_score: number
  highest_tile: number
  average_moves: number
  average_duration_seconds: number
  average_latency_ms: number
  total_calls: number
  total_input_tokens: number
  reached_2048_rate: number
  api_errors: number
  average_request_bytes: number
}

export interface StoredGame {
  id?: string
  game_id?: string
  benchmark_id?: string
  strategy: Strategy | 'mixed'
  result: string
  score: number
  highest_tile: number
  moves: number
  jev_calls: number
  average_latency_ms: number | null
  seed: number
  interruption: string | null
  finished_at: string
}

export interface ResultsData {
  comparison: { strategies: Record<Strategy, StrategyStats> }
  games: StoredGame[]
  benchmarks: BenchmarkJob[]
}

export interface BenchmarkJob {
  id: string
  games_per_mode: number
  status: 'queued' | 'running' | 'cancelling' | 'cancelled' | 'completed' | 'failed'
  completed_games: number
  total_games: number
  current_strategy: Strategy | null
  current_seed: number | null
  error: string | null
  comparison?: ResultsData['comparison']
}

