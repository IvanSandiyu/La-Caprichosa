import { useEffect, useRef, useState } from "react";
import type { GridData, IndexPlayer } from "../../lib/api";
import type { TimeMode } from "../../lib/games";
import { api } from "../../lib/api";
import { prettyDate } from "../../lib/format";
import { useGame } from "../../hooks/useGame";
import { Board } from "../../components/Board";
import { GuessBox } from "../../components/GuessBox";
import { GameFooter } from "../../components/GameFooter";
import {
  HowToPlay,
  ResultModal,
  StatsPanel,
  Modal,
} from "../../components/Modals";

type ModalKind = "howto" | "stats" | "result" | null;

function fmtClock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

interface Props {
  timeMode: TimeMode;
  onExit?: () => void;
}

export function GridGame({ timeMode, onExit }: Props) {
  const [grid, setGrid] = useState<GridData | null>(null);
  const [playerIndex, setPlayerIndex] = useState<IndexPlayer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [shakeBox, setShakeBox] = useState(false);
  const [modal, setModal] = useState<ModalKind>(null);
  const [justLost, setJustLost] = useState(false);
  const [revealLoading, setRevealLoading] = useState(false);

  const prevFinished = useRef(false);

  const {
    placements,
    filledCount,
    attempts,
    finished,
    won,
    revealed,
    onReveal,
    surrender,
    timeLimit,
    secondsUsed,
    stats,
    feedback,
    pendingChoice,
    submitGuess,
    confirmChoice,
    cancelChoice,
    resetDay,
  } = useGame(grid, timeMode);

  useEffect(() => {
    api
      .getGrid()
      .then(setGrid)
      .catch(() =>
        setError("No se pudo contactar el servidor. ¿Está corriendo uvicorn?"),
      );
    api
      .getPlayerIndex()
      .then(setPlayerIndex)
      .catch(() => setPlayerIndex([]));
  }, []);

  // detectar el instante exacto de derrota para el flash
  useEffect(() => {
    if (finished && !won && !prevFinished.current) {
      setJustLost(true);
      const t = setTimeout(() => setJustLost(false), 1800);
      return () => clearTimeout(t);
    }
  }, [finished, won]);

  // si ganó, modal de resultado directo
  useEffect(() => {
    if (finished && won) setModal("result");
  }, [finished, won]);

  const handleReveal = async () => {
    setRevealLoading(true);
    await onReveal();
    setRevealLoading(false);
    setModal("result");
  };

  useEffect(() => {
    prevFinished.current = finished;
  }, [finished]);

  const handleSubmit = async (player: {
    player_id: number;
    name: string;
    image_url: string | null;
  }) => {
    const outcome = await submitGuess(player);
    if (outcome === "miss") {
      setShakeBox(true);
      setTimeout(() => setShakeBox(false), 450);
    }
  };

  const candidateIndices = pendingChoice
    ? pendingChoice.cells.map((c) => c.row * 3 + c.col)
    : null;

  const clock =
    timeLimit !== null ? Math.max(0, timeLimit - secondsUsed) : secondsUsed;
  const urgent = timeLimit !== null && clock <= 10;

  return (
    <>
      {/* flash rojo al perder — estilo eliminación */}
      {justLost && (
        <div
          className="pointer-events-none fixed inset-0 z-50 animate-[eliminate_1.8s_ease-out_forwards]"
          style={{ backgroundColor: "rgba(239, 68, 68, 0.22)" }}
        />
      )}

      {/* header */}
      <header className="flex w-full items-center justify-between border-b border-white/5 py-5">
        <div>
          <h1
            onClick={onExit}
            title={onExit ? "Volver al menú" : undefined}
            className={[
              "bg-gradient-to-r from-sky-300 via-white to-amber-200 bg-clip-text text-2xl font-black tracking-tight text-transparent",
              onExit ? "cursor-pointer transition hover:from-sky-200 hover:to-amber-100" : "",
            ].join(" ")}
          >
            LA CAPRICHOSA
          </h1>
          {grid && (
            <p className="text-xs capitalize text-white/50">
              {prettyDate(grid.date)}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          {onExit && (
            <button
              onClick={onExit}
              className="rounded-lg border border-white/15 px-3 py-1.5 text-xs font-semibold text-white/80 transition hover:bg-white/5"
            >
              ← Menú
            </button>
          )}
          <button
            onClick={() => setModal("howto")}
            className="rounded-lg border border-white/15 px-3 py-1.5 text-xs font-semibold text-white/80 transition hover:bg-white/5"
          >
            Cómo jugar
          </button>
          <button
            onClick={() => setModal("stats")}
            className="rounded-lg border border-white/15 px-3 py-1.5 text-xs font-semibold text-white/80 transition hover:bg-white/5"
          >
            Stats
          </button>
        </div>
      </header>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          {error}
        </div>
      )}

      {!grid && !error && (
        <p className="py-16 text-center text-white/40">Cargando la grilla…</p>
      )}

      {grid && (
        <>
          {/* HUD */}
          <div className="mb-3 flex flex-wrap items-center justify-center gap-2">
            <span
              className={[
                "rounded-lg px-2 py-0.5 font-mono text-base font-bold tabular-nums",
                urgent
                  ? "bg-red-500/15 text-red-300"
                  : "bg-sky-400/10 text-sky-200",
              ].join(" ")}
            >
              {fmtClock(clock)}
            </span>
            <span className="text-[11px] text-white/40">
              · {filledCount}/9 · {attempts} intentos
            </span>
            {revealed && (
              <span className="rounded-lg bg-amber-500/15 px-2 py-0.5 text-[11px] font-bold text-amber-300">
                RESPUESTAS REVELADAS
              </span>
            )}
          </div>

          {/* grilla */}
          <main className="flex w-full flex-1 flex-col items-center gap-3">
            <Board
              grid={grid}
              placements={placements}
              candidateIndices={candidateIndices}
              onChooseCell={confirmChoice}
            />

            {/* entrada de jugadores */}
            {!finished && !pendingChoice && (
              <GuessBox
                index={playerIndex}
                disabled={false}
                shaking={shakeBox}
                onSubmit={handleSubmit}
              />
            )}

            {pendingChoice && (
              <div className="flex flex-col items-center gap-2">
                <p className="animate-pop rounded-lg bg-amber-400/15 px-4 py-2 text-sm font-medium text-amber-200">
                  ¿Dónde ubicás a <b>{pendingChoice.player.name}</b>? Hacé
                  click en una casilla resaltada.
                </p>
                <button
                  onClick={cancelChoice}
                  className="text-xs text-white/40 underline-offset-2 hover:text-white/70 hover:underline"
                >
                  Cancelar elección
                </button>
              </div>
            )}

            {feedback && !pendingChoice && (
              <p
                className={[
                  "animate-pop rounded-lg px-4 py-2 text-sm font-medium",
                  feedback.kind === "ok"
                    ? "bg-emerald-500/15 text-emerald-300"
                    : feedback.kind === "miss"
                      ? "bg-red-500/15 text-red-300"
                      : "bg-sky-500/15 text-sky-300",
                ].join(" ")}
              >
                {feedback.text}
              </p>
            )}

            {/* rendirse */}
            {!finished && (
              <button
                onClick={surrender}
                className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs font-bold text-red-300/80 transition hover:bg-red-500/20"
                title="Abandonar y ver las respuestas del día"
              >
                Rendirse
              </button>
            )}

            {/* derrota: botones revelar + reiniciar */}
            {finished && !won && (
              <div className="mt-1 flex items-center gap-3">
                {!revealed && (
                  <button
                    onClick={handleReveal}
                    disabled={revealLoading}
                    className="rounded-xl border border-amber-500/40 bg-amber-500/15 px-5 py-2 text-sm font-bold text-amber-200 transition hover:bg-amber-500/25 disabled:opacity-50"
                  >
                    {revealLoading ? "Cargando…" : "Revelar respuestas"}
                  </button>
                )}
                {revealed && (
                  <button
                    onClick={() => setModal("result")}
                    className="rounded-xl bg-sky-500 px-5 py-2 text-sm font-bold text-slate-950 transition hover:bg-sky-400"
                  >
                    Ver estadísticas
                  </button>
                )}
                <button
                  onClick={resetDay}
                  className="rounded-xl border border-white/15 px-4 py-2 text-sm text-white/70 transition hover:bg-white/5"
                  title="Borra tu progreso de hoy"
                >
                  Reiniciar día
                </button>
              </div>
            )}

            {/* victoria */}
            {finished && won && (
              <div className="mt-1 flex items-center gap-3">
                <button
                  onClick={() => setModal("stats")}
                  className="rounded-xl bg-sky-500 px-5 py-2 text-sm font-bold text-slate-950 transition hover:bg-sky-400"
                >
                  Ver estadísticas
                </button>
                <button
                  onClick={resetDay}
                  className="rounded-xl border border-white/15 px-4 py-2 text-sm text-white/70 transition hover:bg-white/5"
                  title="Borra tu progreso de hoy"
                >
                  Reiniciar día
                </button>
              </div>
            )}
          </main>

          <footer className="pt-6 text-center text-[11px] leading-relaxed text-white/30">
            Datos e imágenes de Transfermarkt vía transfermarkt-datasets (CC0).
            <br />
            Hecho con cariño para hinchas del fútbol argentino ⚽🇦🇷
          </footer>

          <GameFooter />
        </>
      )}

      {/* modales */}
      {modal === "howto" && <HowToPlay onClose={() => setModal(null)} />}

      {modal === "stats" && (
        <Modal title="Tus estadísticas" onClose={() => setModal(null)}>
          <StatsPanel stats={stats} />
        </Modal>
      )}

      {modal === "result" && (
        <ResultModal
          won={won}
          filled={filledCount}
          revealed={revealed}
          streak={stats.streak}
          onStats={() => setModal("stats")}
          onClose={() => setModal(null)}
        />
      )}
    </>
  );
}
