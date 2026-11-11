import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, BrainCircuit, Cpu, Timer, Zap } from 'lucide-react'
import type { Direction, GameState, Strategy } from '../types'

const directions: Direction[] = ['up', 'down', 'left', 'right']
const directionLabel = { up: 'CIMA', down: 'BAIXO', left: 'ESQUERDA', right: 'DIREITA' }
const directionIcon = { up: ArrowUp, down: ArrowDown, left: ArrowLeft, right: ArrowRight }

export function DecisionPanel({ game, onStrategy, disabled }: { game: GameState; onStrategy: (strategy: Strategy) => void; disabled: boolean }) {
  const decision = game.decision
  return (
    <section className="panel decision-panel">
      <div className="panel-heading"><div><span className="eyebrow">SYSTEM ONE</span><h2>JEV Decision Center</h2></div><BrainCircuit className="accent-icon"/></div>
      <div className="strategy-selector"><span>AI STRATEGY</span><div><button className={game.strategy === 'basic' ? 'selected' : ''} disabled={disabled} onClick={() => onStrategy('basic')}>BASIC</button><button className={game.strategy === 'strategic' ? 'selected' : ''} disabled={disabled} onClick={() => onStrategy('strategic')}>STRATEGIC</button></div></div>
      <div className="current-decision">
        <span>DECISÃO ATUAL</span>
        <strong>{game.decision_pending ? 'ANALISANDO…' : decision ? directionLabel[decision.move] : 'AGUARDANDO'}</strong>
        <small>{decision?.origin === 'forced' ? 'Jogada forçada — sem chamada ao JEV' : decision ? 'Escolha retornada pelo JEV' : 'Inicie o autoplay para ver decisões reais'}</small>
      </div>
      <div className="probabilities">
        <span className="section-label">PROBABILIDADES DA ESCOLHA</span>
        {directions.map(direction => {
          const Icon = directionIcon[direction]
          const value = decision?.probabilities[direction]
          const percent = value == null ? 0 : Math.round(value * 100)
          return <div className="probability" key={direction}><div><Icon size={15}/><span>{directionLabel[direction]}</span><strong>{value == null ? '—' : `${percent}%`}</strong></div><div className="bar"><i style={{ width: `${percent}%` }}/></div></div>
        })}
      </div>
      <div className="decision-metrics">
        <div><Zap/><span>Confiança</span><strong>{decision?.confidence == null ? '—' : `${Math.round(decision.confidence * 100)}%`}</strong></div>
        <div><Timer/><span>Latência API</span><strong>{decision?.latency_ms == null ? '—' : `${Math.round(decision.latency_ms)} ms`}</strong></div>
        <div><Cpu/><span>Modelo</span><strong>{decision?.model ?? 'jev-latest'}</strong></div>
      </div>
      <span className="confidence-note">Confiança indica a concentração da distribuição; não garante a qualidade estratégica.</span>
      <details className="move-analysis" open={game.strategy === 'strategic'}>
        <summary>MOVE ANALYSIS <span>{decision?.strategy === 'strategic' ? `${decision.legal_move_count} opções` : 'disponível no Strategic'}</span></summary>
        {decision?.move_analysis && Object.keys(decision.move_analysis).length > 0 ? <div className="analysis-table"><div className="analysis-row analysis-head"><span>Direção</span><span>Vazios</span><span>Fusões</span><span>Pontos</span></div>{directions.filter(direction => decision.move_analysis[direction]).map(direction => { const item = decision.move_analysis[direction]!; return <div className={`analysis-row ${decision.move === direction ? 'chosen' : ''}`} key={direction}><span>{directionLabel[direction]}</span><span>{item.empty_cells_after}</span><span>{item.merge_count}</span><span>{item.score_gain}</span></div> })}</div> : <p>Os fatos calculados aparecerão após uma decisão Strategic.</p>}
      </details>
    </section>
  )
}

