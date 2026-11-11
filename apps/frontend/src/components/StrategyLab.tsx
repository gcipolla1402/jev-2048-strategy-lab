import { useCallback, useEffect, useState } from 'react'
import { BarChart3, Download, FlaskConical, Square, Trophy } from 'lucide-react'
import { labApi } from '../api'
import type { BenchmarkJob, GameState, ResultsData } from '../types'

const emptyResults: ResultsData = {
  comparison: {
    strategies: {
      basic: { games: 0, completed_games: 0, average_score: 0, max_score: 0, highest_tile: 0, average_moves: 0, average_duration_seconds: 0, average_latency_ms: 0, total_calls: 0, total_input_tokens: 0, reached_2048_rate: 0, api_errors: 0, average_request_bytes: 0 },
      strategic: { games: 0, completed_games: 0, average_score: 0, max_score: 0, highest_tile: 0, average_moves: 0, average_duration_seconds: 0, average_latency_ms: 0, total_calls: 0, total_input_tokens: 0, reached_2048_rate: 0, api_errors: 0, average_request_bytes: 0 },
    },
  },
  games: [],
  benchmarks: [],
}

const labels = {
  average_score: 'Pontuação média',
  max_score: 'Pontuação máxima',
  highest_tile: 'Maior peça',
  average_moves: 'Média de movimentos',
  average_latency_ms: 'Latência média',
  total_calls: 'Chamadas JEV',
  total_input_tokens: 'Tokens de entrada',
  reached_2048_rate: 'Chegaram a 2048',
  api_errors: 'Erros de API',
  average_request_bytes: 'Requisição média',
} as const

export function StrategyLab({ game }: { game: GameState }) {
  const [results, setResults] = useState<ResultsData>(emptyResults)
  const [gamesPerMode, setGamesPerMode] = useState<1 | 5 | 10>(1)
  const [job, setJob] = useState<BenchmarkJob | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try { setResults(await labApi.results()) }
    catch (problem) { setError((problem as Error).message) }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  useEffect(() => {
    if (!job || !['queued', 'running', 'cancelling'].includes(job.status)) return
    const timer = window.setInterval(async () => {
      try {
        const next = await labApi.benchmark(job.id)
        setJob(next)
        if (['completed', 'cancelled', 'failed'].includes(next.status)) void refresh()
      } catch (problem) { setError((problem as Error).message) }
    }, 1200)
    return () => window.clearInterval(timer)
  }, [job, refresh])

  const run = async () => {
    setError(null)
    try { setJob(await labApi.startBenchmark(gamesPerMode)) }
    catch (problem) { setError((problem as Error).message) }
  }

  const cancel = async () => {
    if (!job) return
    try { setJob(await labApi.cancelBenchmark(job.id)) }
    catch (problem) { setError((problem as Error).message) }
  }

  const basic = results.comparison.strategies.basic
  const strategic = results.comparison.strategies.strategic
  const metrics = Object.keys(labels) as (keyof typeof labels)[]
  const progress = job?.total_games ? Math.round((job.completed_games / job.total_games) * 100) : 0

  return (
    <section className="strategy-lab">
      <div className="lab-header"><div><span className="eyebrow">EXPERIMENTOS CONTROLADOS</span><h2><FlaskConical/> AI Strategy Lab</h2><p>O Python calcula consequências imediatas. O JEV continua escolhendo cada movimento.</p></div><div className="lab-current"><span>ESTRATÉGIA ATUAL</span><strong>{game.strategy.toUpperCase()}</strong><small>Seed {game.seed}</small></div></div>
      <div className="lab-grid">
        <div className="comparison-card">
          <div className="lab-card-title"><div><BarChart3/><span>AI PERFORMANCE COMPARISON</span></div><small>{basic.games + strategic.games} partidas registradas</small></div>
          <div className="comparison-table">
            <div className="comparison-row comparison-head"><span>Métrica</span><strong>BASIC</strong><strong>STRATEGIC</strong></div>
            {metrics.map(metric => <div className="comparison-row" key={metric}><span>{labels[metric]}</span><strong>{formatMetric(metric, basic[metric])}</strong><strong>{formatMetric(metric, strategic[metric])}</strong></div>)}
          </div>
        </div>
        <div className="benchmark-card">
          <div className="lab-card-title"><div><Trophy/><span>RUN COMPARISON</span></div></div>
          <p>Executa BASIC e STRATEGIC com as mesmas seeds e limites controlados. Cada clique inicia chamadas reais ao JEV.</p>
          <label>PARTIDAS POR MODO</label>
          <div className="benchmark-count">{([1, 5, 10] as const).map(count => <button className={gamesPerMode === count ? 'selected' : ''} disabled={Boolean(job && ['queued', 'running', 'cancelling'].includes(job.status))} onClick={() => setGamesPerMode(count)} key={count}>{count}<small>{count * 2} total</small></button>)}</div>
          {job && <div className="benchmark-progress"><div><span>{job.status.toUpperCase()}</span><strong>{job.completed_games}/{job.total_games}</strong></div><div className="progress-track"><i style={{ width: `${progress}%` }}/></div><small>{job.current_strategy ? `${job.current_strategy.toUpperCase()} • seed ${job.current_seed}` : job.error ?? 'Aguardando'}</small></div>}
          {error && <span className="lab-error">{error}</span>}
          <div className="benchmark-actions"><button className="run-comparison" disabled={Boolean(job && ['queued', 'running', 'cancelling'].includes(job.status))} onClick={run}><FlaskConical/> RUN COMPARISON</button>{job && ['queued', 'running', 'cancelling'].includes(job.status) && <button className="cancel-benchmark" onClick={cancel}><Square/> CANCELAR</button>}</div>
          <div className="export-actions"><span>EXPORT RESULTS</span><a href={labApi.exportUrl('json')}><Download/> JSON</a><a href={labApi.exportUrl('csv')}><Download/> CSV</a></div>
        </div>
      </div>
      <div className="experiment-history"><div className="lab-card-title"><div><FlaskConical/><span>HISTÓRICO DOS EXPERIMENTOS</span></div></div><div className="experiment-list">{results.games.length === 0 && <p>Nenhum resultado registrado ainda.</p>}{results.games.slice(0, 12).map((item, index) => <article key={item.id ?? `${item.finished_at}-${index}`}><span className={`strategy-pill ${item.strategy}`}>{item.strategy.toUpperCase()}</span><strong>{item.score.toLocaleString('pt-BR')} pts</strong><span>Peça {item.highest_tile}</span><span>{item.moves} mov.</span><span>Seed {item.seed}</span><span className={`result-pill ${item.result}`}>{item.interruption ? 'INTERROMPIDA' : item.result.toUpperCase()}</span></article>)}</div></div>
    </section>
  )
}

function formatMetric(metric: keyof typeof labels, value: number) {
  if (metric === 'average_latency_ms') return value ? `${Math.round(value)} ms` : '—'
  if (metric === 'reached_2048_rate') return `${value}%`
  if (metric === 'average_request_bytes') return value ? `${Math.round(value)} B` : '—'
  return value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
}

