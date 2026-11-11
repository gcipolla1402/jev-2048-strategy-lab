import { useCallback, useEffect, useRef, useState } from 'react'
import { Bot, ShieldCheck } from 'lucide-react'
import { gameApi } from './api'
import { DecisionPanel } from './components/DecisionPanel'
import { GameBoard } from './components/GameBoard'
import { GameControls, type Speed } from './components/GameControls'
import { MoveHistory } from './components/MoveHistory'
import { StatsBar } from './components/StatsBar'
import { StrategyLab } from './components/StrategyLab'
import type { Direction, GameState, Strategy } from './types'

const delays: Record<Speed, number> = { slow: 1800, normal: 850, fast: 280 }

function App() {
  const [game, setGame] = useState<GameState | null>(null)
  const createStarted = useRef(false)
  const [speed, setSpeed] = useState<Speed>('normal')
  const [running, setRunning] = useState(false)
  const [busy, setBusy] = useState(false)
  const [fatalError, setFatalError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const gameRef = useRef<GameState | null>(null)
  const runToken = useRef(0)
  const receivedAt = useRef(Date.now())

  const updateGame = useCallback((next: GameState) => {
    gameRef.current = next
    receivedAt.current = Date.now()
    setGame(next)
    setFatalError(null)
  }, [])

  useEffect(() => {
    if (createStarted.current) return
    createStarted.current = true
    gameApi.create().then(updateGame).catch(error => setFatalError(error.message))
  }, [updateGame])

  useEffect(() => {
    const interval = window.setInterval(() => setTick(value => value + 1), 1000)
    return () => window.clearInterval(interval)
  }, [])

  const pause = useCallback(async () => {
    runToken.current += 1
    setRunning(false)
    const current = gameRef.current
    if (!current) return
    try { updateGame(await gameApi.control(current.id, 'pause')) }
    catch (error) { setFatalError((error as Error).message) }
  }, [updateGame])

  const runAutoplay = useCallback(async (token: number) => {
    while (runToken.current === token) {
      const current = gameRef.current
      if (!current || current.status === 'game_over') break
      setBusy(true)
      try {
        const next = await gameApi.next(current.id, current.generation, current.state_version)
        if (runToken.current !== token) break
        updateGame(next)
        if (next.status === 'game_over') break
      } catch (error) {
        if (runToken.current === token) setFatalError((error as Error).message)
        break
      } finally {
        setBusy(false)
      }
      await new Promise(resolve => window.setTimeout(resolve, delays[speed]))
    }
    if (runToken.current === token) setRunning(false)
  }, [speed, updateGame])

  const start = useCallback(async () => {
    const current = gameRef.current
    if (!current || running) return
    setFatalError(null)
    try {
      updateGame(await gameApi.control(current.id, current.mode === 'jev' ? 'resume' : 'jev'))
      const token = ++runToken.current
      setRunning(true)
      void runAutoplay(token)
    } catch (error) { setFatalError((error as Error).message) }
  }, [runAutoplay, running, updateGame])

  const nextMove = useCallback(async () => {
    const current = gameRef.current
    if (!current || busy) return
    setBusy(true)
    setFatalError(null)
    try {
      let ready = current
      if (current.mode !== 'jev' || current.status === 'paused') ready = await gameApi.control(current.id, 'jev')
      updateGame(await gameApi.next(ready.id, ready.generation, ready.state_version))
    } catch (error) { setFatalError((error as Error).message) }
    finally { setBusy(false) }
  }, [busy, updateGame])

  const restart = useCallback(async () => {
    const current = gameRef.current
    if (!current) return
    runToken.current += 1
    setRunning(false)
    setBusy(false)
    try { updateGame(await gameApi.restart(current.id)) }
    catch (error) { setFatalError((error as Error).message) }
  }, [updateGame])

  const manualMode = useCallback(async () => {
    const current = gameRef.current
    if (!current) return
    runToken.current += 1
    setRunning(false)
    try { updateGame(await gameApi.control(current.id, 'manual')) }
    catch (error) { setFatalError((error as Error).message) }
  }, [updateGame])

  const changeStrategy = useCallback(async (strategy: Strategy) => {
    const current = gameRef.current
    if (!current || current.strategy === strategy) return
    runToken.current += 1
    setRunning(false)
    setFatalError(null)
    try {
      if (running || current.decision_pending) await gameApi.control(current.id, 'pause')
      updateGame(await gameApi.strategy(current.id, strategy))
    } catch (error) { setFatalError((error as Error).message) }
  }, [running, updateGame])

  const manualMove = useCallback(async (direction: Direction) => {
    const current = gameRef.current
    if (!current || current.mode !== 'manual' || busy || current.status === 'game_over') return
    setBusy(true)
    try { updateGame(await gameApi.move(current.id, direction)) }
    catch (error) { setFatalError((error as Error).message) }
    finally { setBusy(false) }
  }, [busy, updateGame])

  useEffect(() => {
    const mapping: Record<string, Direction> = { ArrowUp: 'up', w: 'up', W: 'up', ArrowDown: 'down', s: 'down', S: 'down', ArrowLeft: 'left', a: 'left', A: 'left', ArrowRight: 'right', d: 'right', D: 'right' }
    const handleKey = (event: KeyboardEvent) => {
      const direction = mapping[event.key]
      if (!direction) return
      event.preventDefault()
      void manualMove(direction)
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [manualMove])

  if (!game) return <main className="loading-screen"><div className="loader"><Bot/><span>{fatalError ?? 'Preparando a partida…'}</span></div></main>

  const elapsed = game.elapsed_seconds + Math.floor((Date.now() - receivedAt.current) / 1000) + tick * 0
  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-mark"><Bot size={24}/></div>
        <div className="brand"><h1>JEV <span>2048</span></h1><p>Watch AI Make Every Move</p></div>
        <div className="api-badge"><span></span><div><strong>TYPESAFE SYSTEM ONE</strong><small>Decisões reais via JEV</small></div><ShieldCheck size={18}/></div>
      </header>
      <StatsBar game={game} elapsed={elapsed}/>
      {fatalError && <div className="error-banner" role="alert"><strong>Autoplay pausado.</strong><span>{fatalError}</span><button onClick={() => setFatalError(null)}>FECHAR</button></div>}
      {game.status === 'won' && <div className="win-banner"><strong>2048 alcançado!</strong><span>Você pode continuar jogando ou reiniciar a partida.</span></div>}
      <section className="main-grid">
        <GameBoard game={game}/>
        <GameControls game={game} running={running} busy={busy} speed={speed} onStart={start} onPause={pause} onNext={nextMove} onRestart={restart} onManual={manualMode} onSpeed={setSpeed}/>
        <DecisionPanel game={game} onStrategy={changeStrategy} disabled={game.status === 'game_over'}/>
      </section>
      <MoveHistory game={game}/>
      <StrategyLab game={game}/>
      <footer><span>JEV 2048</span><span>Motor determinístico • Decisões JEV via TypeSafe API • Sem decisões simuladas</span></footer>
    </main>
  )
}

export default App

