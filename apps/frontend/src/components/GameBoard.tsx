import type { GameState } from '../types'

const tileClass = (value: number) => `tile tile-${Math.min(value, 4096)}`

export function GameBoard({ game }: { game: GameState }) {
  const merged = new Set(game.merged_positions.map(([row, col]) => `${row}-${col}`))
  return (
    <section className="board-shell" aria-label="Tabuleiro 2048">
      <div className="board-caption">
        <span>PARTIDA ATUAL</span>
        <span>{game.mode === 'jev' ? 'JEV ONLINE' : 'CONTROLE MANUAL'}</span>
      </div>
      <div className={`board board--${game.last_direction ?? 'idle'} board--${game.status}`}>
        {game.board.flatMap((row, rowIndex) =>
          row.map((value, colIndex) => {
            const key = `${rowIndex}-${colIndex}`
            const isNew = game.spawned_at?.[0] === rowIndex && game.spawned_at?.[1] === colIndex
            return (
              <div className="cell" key={key}>
                {value > 0 && (
                  <div className={`${tileClass(value)} ${isNew ? 'tile--new' : ''} ${merged.has(key) ? 'tile--merged' : ''}`}>
                    {value}
                  </div>
                )}
              </div>
            )
          }),
        )}
      </div>
      {game.status === 'game_over' && <div className="game-over-overlay"><strong>FIM DE JOGO</strong><span>Reinicie para tentar novamente</span></div>}
      <div className="keyboard-hint"><kbd>↑</kbd><kbd>↓</kbd><kbd>←</kbd><kbd>→</kbd><span>ou WASD no modo manual</span></div>
    </section>
  )
}

