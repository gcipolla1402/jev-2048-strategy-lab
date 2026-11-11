import { Activity, Clock3, Crown, Gauge, Sparkles } from 'lucide-react'
import type { GameState } from '../types'

const statusLabels = { playing: 'Jogando', paused: 'Pausado', won: '2048!', game_over: 'Fim de jogo' }
const formatTime = (seconds: number) => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`

export function StatsBar({ game, elapsed }: { game: GameState; elapsed: number }) {
  const items = [
    { icon: Gauge, label: 'Pontuação', value: game.score.toLocaleString('pt-BR'), animated: true },
    { icon: Crown, label: 'Maior peça', value: game.highest_tile.toLocaleString('pt-BR') },
    { icon: Sparkles, label: 'Movimentos', value: game.total_moves.toLocaleString('pt-BR') },
    { icon: Activity, label: 'Status da IA', value: game.mode === 'jev' ? statusLabels[game.status] : 'Manual' },
    { icon: Clock3, label: 'Tempo', value: formatTime(elapsed) },
  ]
  return <section className="stats-bar">{items.map(({ icon: Icon, label, value, animated }) => <div className="stat" key={label}><Icon size={17}/><div><span>{label}</span><strong className={animated ? 'score-value' : ''} key={animated ? game.score : label}>{value}</strong></div></div>)}</section>
}

