import { Bot, Pause, Play, RefreshCw, StepForward, UserRound } from 'lucide-react'
import type { GameState } from '../types'

export type Speed = 'slow' | 'normal' | 'fast'

interface Props {
  game: GameState
  running: boolean
  speed: Speed
  busy: boolean
  onStart: () => void
  onPause: () => void
  onNext: () => void
  onRestart: () => void
  onManual: () => void
  onSpeed: (speed: Speed) => void
}

export function GameControls(props: Props) {
  const { game, running, speed, busy } = props
  return (
    <section className="panel controls-panel">
      <div className="panel-heading"><div><span className="eyebrow">CONTROLES</span><h2>Comando da partida</h2></div><span className={`status-dot ${running ? 'active' : ''}`}/></div>
      <button className="primary-action" onClick={props.onStart} disabled={running || game.status === 'game_over'}>
        {game.mode === 'jev' && game.status === 'paused' ? <Play/> : <Bot/>}
        {game.mode === 'jev' && game.status === 'paused' ? 'RESUME JEV' : 'START JEV AI'}
      </button>
      <div className="control-grid">
        <button onClick={props.onPause} disabled={!running}><Pause/> PAUSE</button>
        <button onClick={props.onNext} disabled={running || busy || game.status === 'game_over'}><StepForward/> NEXT MOVE</button>
        <button onClick={props.onRestart}><RefreshCw/> RESTART</button>
        <button onClick={props.onManual} disabled={running}><UserRound/> MANUAL MODE</button>
      </div>
      <div className="speed-control">
        <span>VELOCIDADE VISUAL</span>
        <div>{(['slow', 'normal', 'fast'] as Speed[]).map(item => <button className={speed === item ? 'selected' : ''} onClick={() => props.onSpeed(item)} key={item}>{item.toUpperCase()}</button>)}</div>
      </div>
      <div className="mini-stats">
        <div><span>Melhor da sessão</span><strong>{game.best_score.toLocaleString('pt-BR')}</strong></div>
        <div><span>Chamadas JEV</span><strong>{game.metrics.total_jev_calls}</strong></div>
        <div><span>Latência média</span><strong>{game.metrics.average_latency_ms ? `${Math.round(game.metrics.average_latency_ms)} ms` : '—'}</strong></div>
        <div><span>Erros de API</span><strong>{game.metrics.api_errors}</strong></div>
      </div>
    </section>
  )
}

