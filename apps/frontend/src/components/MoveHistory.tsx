import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, History } from 'lucide-react'
import type { Direction, GameState } from '../types'

const labels = { up: 'CIMA', down: 'BAIXO', left: 'ESQUERDA', right: 'DIREITA' }
const icons = { up: ArrowUp, down: ArrowDown, left: ArrowLeft, right: ArrowRight }
const origin = { jev: 'JEV', forced: 'FORÇADA', manual: 'MANUAL' }

export function MoveHistory({ game }: { game: GameState }) {
  return (
    <section className="panel history-panel">
      <div className="history-title"><div><History size={17}/><span>HISTÓRICO DE MOVIMENTOS</span></div><span>{game.history.length} registros</span></div>
      <div className="history-list">
        {!game.history.length && <div className="empty-history">As decisões aparecerão aqui durante a partida.</div>}
        {game.history.map(item => {
          const Icon = icons[item.move as Direction]
          return <article key={item.number}><span className="move-number">#{String(item.number).padStart(2, '0')}</span><span className="move-direction"><Icon size={15}/>{labels[item.move]}</span><span className={`origin origin-${item.origin}`}>{origin[item.origin]}</span><span>Score <b>{item.score.toLocaleString('pt-BR')}</b></span><span>{item.latency_ms == null ? '—' : `${Math.round(item.latency_ms)} ms`}</span><span>{item.confidence == null ? '—' : `${Math.round(item.confidence * 100)}% conf.`}</span></article>
        })}
      </div>
    </section>
  )
}

