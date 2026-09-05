import { useCallback, useEffect, useMemo, useState } from "react";
import type { Difficulty, ImpostorPuzzleData } from "../../lib/api";
import { api } from "../../lib/api";
import { todayKey } from "../../lib/format";
import type { ImpostorMode } from "../../lib/games";
import { Silhouette } from "../../components/Silhouette";
import { GameFooter } from "../../components/GameFooter";
import { GameHeader } from "../../components/GameHeader";
import { useGameStats } from "../../hooks/useGameStats";

interface Props {
  difficulty: Difficulty;
  mode: ImpostorMode;
  onExit?: () => void;
}

interface SavedState {
  date: string;
  difficulty: Difficulty;
  mode: ImpostorMode;
  won: boolean;
}

const KEY = "impostor";

function loadSaved(difficulty: Difficulty, mode: ImpostorMode): SavedState | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const s: SavedState = JSON.parse(raw);
    if (s.date === todayKey() && s.difficulty === difficulty && s.mode === mode) return s;
    return null;
  } catch {
    return null;
  }
}

function saveResult(difficulty: Difficulty, mode: ImpostorMode, won: boolean) {
  localStorage.setItem(
    KEY,
    JSON.stringify({ date: todayKey(), difficulty, mode, won }),
  );
}

function PlayerFace({
  name,
  imageUrl,
  size = "md",
  dim,
}: {
  name: string;
  imageUrl: string | null;
  size?: "sm" | "md";
  dim?: boolean;
}) {
  return (
    <div
      className={[
        "flex flex-col items-center gap-1",
        dim ? "opacity-40" : "",
      ].join(" ")}
    >
      <div
        className={[
          "aspect-square overflow-hidden rounded-xl border border-white/15 bg-slate-800",
          size === "md" ? "w-full max-w-[92px]" : "w-12",
        ].join(" ")}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={name}
            loading="lazy"
            className="h-full w-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Silhouette className="h-3/5 w-3/5 text-white/20" />
          </div>
        )}
      </div>
      <span className="block w-full truncate text-center text-[9px] font-bold leading-tight text-white/80">
        {name}
      </span>
    </div>
  );
}

export function ImpostorGame({ difficulty, mode, onExit }: Props) {
  const [puzzle, setPuzzle] = useState<ImpostorPuzzleData | null>(null);
  const [error, setError] = useState(false);
  // jugadores marcados como "correcto" (solo modo normal)
  const [selected, setSelected] = useState<Set<number>>(new Set());
  // ids confirmados correctos en modo uno-a-uno
  const [locked, setLocked] = useState<Set<number>>(new Set());
  // jugador elegido en modo uno-a-uno (pendiente de confirmar con "Check")
  const [candidate, setCandidate] = useState<number | null>(null);
  const [gameOver, setGameOver] = useState(false);
  const [won, setWon] = useState(false);
  const [justLost, setJustLost] = useState(false);

  const gs = useGameStats("impostor", todayKey());

  const saved = useMemo(() => loadSaved(difficulty, mode), [difficulty, mode]);

  useEffect(() => {
    if (saved) {
      setGameOver(true);
      setWon(saved.won);
    }
  }, [saved]);

  useEffect(() => {
    if (saved) return;
    api
      .getImpostor(difficulty)
      .then(setPuzzle)
      .catch(() => setError(true));
  }, [difficulty, saved]);

  const toggle = useCallback((id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // modo normal: confirmar selección
  const submitNormal = useCallback(() => {
    if (!puzzle || gameOver) return;
    const correctIds = puzzle.players.filter((p) => !p.is_impostor).map((p) => p.id);
    const allCorrectSelected = correctIds.every((id) => selected.has(id));
    const noImpostor = !puzzle.players.some((p) => p.is_impostor && selected.has(p.id));
    if (allCorrectSelected && noImpostor) {
      setWon(true);
      setGameOver(true);
      gs.registerResult(true);
      saveResult(difficulty, mode, true);
    } else {
      setWon(false);
      setGameOver(true);
      setJustLost(true);
      gs.registerResult(false);
      saveResult(difficulty, mode, false);
    }
  }, [puzzle, gameOver, selected, difficulty, mode, gs.registerResult]);

  // modo uno-a-uno: elegir un jugador y confirmarlo con "Check"
  const selectCandidate = useCallback(
    (id: number) => {
      if (!puzzle || gameOver || locked.has(id)) return;
      setCandidate((prev) => (prev === id ? null : id));
    },
    [puzzle, gameOver, locked],
  );

  const verifyCandidate = useCallback(() => {
    if (!puzzle || gameOver || candidate === null) return;
    const p = puzzle.players.find((x) => x.id === candidate);
    if (!p) return;
    const correctIds = puzzle.players.filter((x) => !x.is_impostor).map((x) => x.id);
    if (!p.is_impostor) {
      const next = new Set(locked);
      next.add(p.id);
      setLocked(next);
      setCandidate(null);
      const allCorrect = correctIds.every((id) => next.has(id));
      if (allCorrect) {
        setWon(true);
        setGameOver(true);
        gs.registerResult(true);
        saveResult(difficulty, mode, true);
      }
    } else {
      setWon(false);
      setGameOver(true);
      setJustLost(true);
      gs.registerResult(false);
      saveResult(difficulty, mode, false);
    }
  }, [puzzle, gameOver, candidate, locked, difficulty, mode, gs.registerResult]);

  if (error) {
    return (
      <div className="flex w-full flex-col items-center gap-4 pt-10">
        <p className="text-sm text-red-400">Error al cargar el puzzle.</p>
        <button onClick={onExit} className="text-sm text-sky-400 underline">Volver</button>
      </div>
    );
  }

  if (!puzzle) {
    return (
      <div className="flex w-full items-center justify-center pt-20">
        <p className="text-sm text-white/40">Cargando...</p>
      </div>
    );
  }

  const correctIds = new Set(puzzle.players.filter((p) => !p.is_impostor).map((p) => p.id));

  // estado visual de cada jugador
  const stateFor = (p: ImpostorPuzzleData["players"][number]) => {
    if (gameOver) {
      if (p.is_impostor) return "impostor";
      return "correct";
    }
    if (mode === "normal") {
      return selected.has(p.id) ? "selected" : "idle";
    }
    // uno a uno
    if (locked.has(p.id)) return "locked";
    if (p.id === candidate) return "candidate";
    return "idle";
  };

  const handleClick = (id: number) => {
    if (gameOver) return;
    if (mode === "normal") toggle(id);
    else selectCandidate(id);
  };

  const ringColor = (state: string) => {
    switch (state) {
      case "selected":
        return "border-sky-400 ring-2 ring-sky-400/70";
      case "candidate":
        return "border-amber-400 ring-2 ring-amber-400/80";
      case "locked":
        return "border-emerald-400/80";
      case "correct":
        return "border-emerald-400 ring-2 ring-emerald-400/70";
      case "impostor":
        return "border-red-500 ring-2 ring-red-500/80";
      default:
        return "border-white/15";
    }
  };

  return (
    <div className="flex w-full flex-col items-center gap-5 pt-4">
      {justLost && !won && (
        <div
          className="pointer-events-none fixed inset-0 z-50 animate-[eliminate_1.8s_ease-out_forwards]"
          style={{ backgroundColor: "rgba(239, 68, 68, 0.22)" }}
        />
      )}

      {/* header */}
      <GameHeader
        gameId="impostor"
        subtitle={`El Impostor · ${mode === "normal" ? "Normal" : "Uno a uno"}`}
        onExit={onExit}
        stats={gs.stats}
      />

      {/* categoría */}
      <div className="w-full rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-center">
        <p className="text-[10px] font-bold uppercase tracking-widest text-white/40">Categoría</p>
        <p className="mt-1 text-base font-black text-sky-200">{puzzle.category}</p>
        {mode === "normal" && !gameOver && (
          <p className="mt-1 text-[11px] text-white/50">
            Seleccioná a todos los que cumplen la categoría (x{correctIds.size})
          </p>
        )}
        {mode === "uno-a-uno" && (
          <p className="mt-1 text-[11px] text-white/50">
            Tocá un rostro y confirmá con <span className="font-bold text-amber-300">Check</span>. Si elegís al impostor, perdés.
          </p>
        )}
      </div>

      {/* tablero */}
      <div className="grid w-full max-w-md grid-cols-3 gap-2 sm:grid-cols-3">
        {puzzle.players.map((p) => {
          const state = stateFor(p);
          let label: string | null = null;
          if (gameOver) {
            label = p.is_impostor ? "Impostor" : "Correcto";
          } else if (mode === "normal" && selected.has(p.id)) {
            label = "✓";
          } else if (mode === "uno-a-uno" && locked.has(p.id)) {
            label = "✓";
          } else if (mode === "uno-a-uno" && p.id === candidate) {
            label = "?";
          }
          return (
            <button
              key={p.id}
              onClick={() => handleClick(p.id)}
              disabled={gameOver || (mode === "uno-a-uno" && locked.has(p.id) && !gameOver)}
              className={[
                "relative rounded-2xl border bg-white/[0.04] p-2 transition",
                ringColor(state),
                !gameOver ? "hover:bg-white/[0.08]" : "",
              ].join(" ")}
            >
              <PlayerFace name={p.name} imageUrl={p.image_url} dim={gameOver && p.is_impostor} />
              {label && (
                <span
                  className={[
                    "absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-black",
                    gameOver && p.is_impostor ? "bg-red-500 text-white" : "bg-emerald-500 text-white",
                  ].join(" ")}
                >
                  {label === "Impostor" ? "✗" : label === "Correcto" ? "✓" : label}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* feedback */}
      {gameOver && (
        <div
          className={[
            "w-full max-w-md rounded-2xl px-4 py-3 text-center font-black",
            won ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/20 text-red-300",
          ].join(" ")}
        >
          {won ? "¡Ganaste!" : "Perdiste — tocaste un impostor"}
        </div>
      )}

      {/* acción */}
      {mode === "normal" && !gameOver && (
        <button
          onClick={submitNormal}
          disabled={selected.size === 0}
          className="w-full max-w-md rounded-xl bg-sky-500 px-4 py-3 text-sm font-black uppercase tracking-wide text-slate-950 transition hover:bg-sky-400 disabled:opacity-30"
        >
          Confirmar selección
        </button>
      )}

      {mode === "uno-a-uno" && candidate !== null && !gameOver && (
        <div className="flex w-full max-w-md flex-col items-center gap-1">
          <button
            onClick={verifyCandidate}
            className="w-full rounded-xl bg-sky-500 px-4 py-3 text-sm font-black uppercase tracking-wide text-slate-950 transition hover:bg-sky-400"
          >
            Check
          </button>
          <p className="text-[11px] text-white/40">¿Este jugador cumple la categoría?</p>
        </div>
      )}

      {gameOver && (
        <button onClick={onExit} className="mt-1 rounded-xl bg-white/10 px-6 py-2.5 text-sm font-bold text-white transition hover:bg-white/15">
          Volver al menú
        </button>
      )}

      <GameFooter />
    </div>
  );
}
