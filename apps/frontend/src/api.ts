import type { BenchmarkJob, Direction, GameState, ResultsData, Strategy } from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail ?? 'Não foi possível concluir a operação.')
  return data
}

export const gameApi = {
  create: () => request<GameState>('/api/games', { method: 'POST' }),
  move: (id: string, direction: Direction) =>
    request<GameState>(`/api/games/${id}/move`, { method: 'POST', body: JSON.stringify({ direction }) }),
  control: (id: string, action: 'pause' | 'manual' | 'jev' | 'resume') =>
    request<GameState>(`/api/games/${id}/control`, { method: 'POST', body: JSON.stringify({ action }) }),
  strategy: (id: string, strategy: Strategy) =>
    request<GameState>(`/api/games/${id}/strategy`, { method: 'POST', body: JSON.stringify({ strategy }) }),
  restart: (id: string) => request<GameState>(`/api/games/${id}/restart`, { method: 'POST' }),
  next: (id: string, generation: number, stateVersion: number) =>
    request<GameState>(`/api/games/${id}/jev/next`, { method: 'POST', body: JSON.stringify({ generation, state_version: stateVersion }) }),
}

export const labApi = {
  results: () => request<ResultsData>('/api/results'),
  startBenchmark: (gamesPerMode: 1 | 5 | 10) => request<BenchmarkJob>('/api/benchmarks', { method: 'POST', body: JSON.stringify({ games_per_mode: gamesPerMode }) }),
  benchmark: (id: string) => request<BenchmarkJob>(`/api/benchmarks/${id}`),
  cancelBenchmark: (id: string) => request<BenchmarkJob>(`/api/benchmarks/${id}/cancel`, { method: 'POST' }),
  exportUrl: (format: 'json' | 'csv') => `/api/results/export?format=${format}`,
}


