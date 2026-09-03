import { useEffect, useMemo, useState } from "react";
import type { PuzzleData, PuzzleGroupData, Difficulty } from "../../lib/api";
import { api } from "../../lib/api";
import { prettyDate } from "../../lib/format";
import { GameFooter } from "../../components/GameFooter";

const MAX_MISTAKES: Record<Difficulty, number | null> = {
  facil: null,
  normal: 4,
  dificil: 3,
};

const GROUP_COLORS = [
  { bg: "bg-amber-400", text: "text-amber-950" },
  { bg: "bg-emerald-400", text: "text-emerald-950" },
  { bg: "bg-sky-400", text: "text-sky-950" },
  { bg: "bg-purple-400", text: "text-purple-950" },
];

function shuffleArray<T>(arr: T[], rng: () => number): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function seededRandom(seed: string): () => number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = (h * 31 + seed.charCodeAt(i)) | 0;
  }
  return () => {
    h = (h * 1664525 + 1013904223) | 0;
    return (h >>> 0) / 4294967296;
  };
}

/* ── types ─────────────────────────────────────────────── */

interface Cell {
  playerId: number;
  name: string;
  imageUrl: string | null;
  groupIndex: number;
}

interface SolvedGroup {
  groupIndex: number;
  name: string;
  groupType: string;
  playerNames: string[];
  imageUrls: (string | null)[];
}

/* ── banner de conexión ────────────────────────────────── */

function ConnectionBanner({
  sg,
  animate,
}: {
  sg: SolvedGroup;
  animate?: boolean;
}) {
  const c = GROUP_COLORS[sg.groupIndex];
  return (
    <div
      className={[
        "flex w-full items-center justify-between rounded-xl px-4 py-3.5",
        c.bg,
        animate ? "animate-[revealBanner_0.8s_cubic-bezier(0.34,1.56,0.64,1)_forwards]" : "",
      ].join(" ")}
    >
      {/* 2 caras izquierda */}
      <div className="flex shrink-0 gap-1.5">
        {(sg.imageUrls ?? []).slice(0, 2).map((url, i) => (
          <div
            key={i}
            className="h-12 w-12 overflow-hidden rounded-lg bg-white/20"
          >
            <img
              src={url ?? undefined}
              alt=""
              className="h-full w-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          </div>
        ))}
      </div>
      {/* texto centrado */}
      <div className="flex min-w-0 flex-1 flex-col items-center px-3">
        <span
          className={`block text-sm font-black uppercase leading-tight ${c.text}`}
        >
          {sg.name}
        </span>
        <span
          className={`block text-center text-[10px] leading-tight opacity-80 ${c.text}`}
        >
          {sg.playerNames.join(" · ")}
        </span>
      </div>
      {/* 2 caras derecha */}
      <div className="flex shrink-0 gap-1.5">
        {(sg.imageUrls ?? []).slice(2, 4).map((url, i) => (
          <div
            key={i}
            className="h-12 w-12 overflow-hidden rounded-lg bg-white/20"
          >
            <img
              src={url ?? undefined}
              alt=""
              className="h-full w-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── componente principal ──────────────────────────────── */

interface Props {
  difficulty: Difficulty;
  onExit?: () => void;
}

export function ConexionesGame({ difficulty, onExit }: Props) {
  const [puzzle, setPuzzle] = useState<PuzzleData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [solved, setSolved] = useState<Map<number, SolvedGroup>>(new Map());
  const [mistakes, setMistakes] = useState(0);
  const [shakeWrong, setShakeWrong] = useState(false);
  const [feedback, setFeedback] = useState<{ kind: "ok" | "miss"; text: string } | null>(null);
  const [oneAway, setOneAway] = useState(false);
  const [justRevealed, setJustRevealed] = useState<number | null>(null);

  const maxMistakes = MAX_MISTAKES[difficulty];

  useEffect(() => {
    api
      .getPuzzle(difficulty)
      .then(setPuzzle)
      .catch(() => setError("No se pudo cargar el puzzle."));
  }, [difficulty]);

  const cells: Cell[] = useMemo(() => {
    if (!puzzle) return [];
    const rng = seededRandom(`conexiones-${puzzle.date}-${difficulty}`);
    const all: Cell[] = [];
    for (const [i, g] of puzzle.groups.entries()) {
      for (let j = 0; j < 4; j++) {
        all.push({
          playerId: g.player_ids[j],
          name: g.player_names[j],
          imageUrl: g.image_urls[j],
          groupIndex: i,
        });
      }
    }
    return shuffleArray(all, rng);
  }, [puzzle, difficulty]);

  const remainingCells = useMemo(
    () => cells.filter((c) => !solved.has(c.groupIndex)),
    [cells, solved],
  );

  const toggle = (idx: number) => {
    if (isGameOver || isWin) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else if (next.size < 4) next.add(idx);
      return next;
    });
  };

  const send = () => {
    if (selected.size !== 4 || !puzzle) return;
    const indices = [...selected];
    const groupIds = indices.map((i) => remainingCells[i].groupIndex);
    const allSame = groupIds.every((id) => id === groupIds[0]);

    if (allSame) {
      const gi = groupIds[0];
      const g: PuzzleGroupData = puzzle.groups[gi];
      setJustRevealed(gi);
      setTimeout(() => setJustRevealed(null), 500);
      setSolved(
        (prev) =>
          new Map(prev).set(gi, {
            groupIndex: gi,
            name: g.name,
            groupType: g.group_type,
            playerNames: g.player_names,
            imageUrls: g.image_urls,
          }),
      );
      setSelected(new Set());
      setFeedback({ kind: "ok", text: `¡${g.name}!` });
      setTimeout(() => setFeedback(null), 1500);
    } else {
      const counts = new Map<number, number>();
      groupIds.forEach((id) => counts.set(id, (counts.get(id) || 0) + 1));
      const maxCount = Math.max(...counts.values());
      if (maxCount === 3) {
        setOneAway(true);
        setTimeout(() => setOneAway(false), 2000);
      }
      setMistakes((m) => m + 1);
      setShakeWrong(true);
      setTimeout(() => setShakeWrong(false), 600);
    }
  };

  const isGameOver = mistakes >= (maxMistakes ?? Infinity);
  const isWin = solved.size === 4;

  const allGroups: SolvedGroup[] = useMemo(() => {
    if (!puzzle) return [];
    return puzzle.groups.map((g, i) => ({
      groupIndex: i,
      name: g.name,
      groupType: g.group_type,
      playerNames: g.player_names,
      imageUrls: g.image_urls,
    }));
  }, [puzzle]);

  if (!puzzle && !error) {
    return <p className="py-16 text-center text-white/40">Cargando puzzle…</p>;
  }
  if (error || !puzzle) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
        {error || "Error desconocido"}
      </div>
    );
  }

  const remaining = maxMistakes !== null ? maxMistakes - mistakes : null;
  const sortedSolved = [...solved.values()].sort(
    (a, b) => a.groupIndex - b.groupIndex,
  );

  /* ── game over: solo mostrar las 4 conexiones ─── */
  if (isGameOver || isWin) {
    return (
      <>
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
            <p className="text-xs capitalize text-white/50">
              Conexiones · {prettyDate(puzzle.date)}
            </p>
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
          </div>
        </header>

        <div className="mb-3 flex flex-wrap items-center justify-center gap-3">
          <span
            className={[
              "rounded-lg px-3 py-1 text-sm font-bold",
              isWin
                ? "bg-emerald-500/15 text-emerald-300"
                : "bg-red-500/15 text-red-300",
            ].join(" ")}
          >
            {isWin
              ? "¡Desarmaste todos los grupos!"
              : "Se acabaron los errores."}
          </span>
        </div>

        <main className="flex w-full max-w-lg flex-1 flex-col items-center justify-center gap-2">
          {allGroups.map((sg) => (
            <ConnectionBanner key={sg.groupIndex} sg={sg} />
          ))}
        </main>

        <footer className="pt-6 text-center text-[11px] leading-relaxed text-white/30">
          Hecho con cariño para hinchas del fútbol argentino ⚽🇦🇷
        </footer>

        <GameFooter />
      </>
    );
  }

  /* ── juego en curso ─── */
  return (
    <>
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
          <p className="text-xs capitalize text-white/50">
            Conexiones · {prettyDate(puzzle.date)}
          </p>
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
        </div>
      </header>

      <div className="mb-3 flex flex-wrap items-center justify-center gap-3">
        <span className="rounded-lg bg-sky-400/10 px-2 py-0.5 text-xs font-bold text-sky-200">
          {solved.size}/4 grupos
        </span>
        {remaining !== null && (
          <span
            className={[
              "rounded-lg px-2 py-0.5 text-xs font-bold",
              remaining <= 1
                ? "bg-red-500/15 text-red-300"
                : "bg-white/10 text-white/60",
            ].join(" ")}
          >
            {remaining} {remaining === 1 ? "error" : "errores"} restantes
          </span>
        )}
        {remaining === null && (
          <span className="rounded-lg bg-white/10 px-2 py-0.5 text-xs text-white/60">
            Sin límite de errores
          </span>
        )}
      </div>

      {feedback && (
        <p
          className={[
            "mb-2 animate-pop rounded-lg px-4 py-2 text-sm font-medium",
            feedback.kind === "ok"
              ? "bg-emerald-500/15 text-emerald-300"
              : "bg-red-500/15 text-red-300",
          ].join(" ")}
        >
          {feedback.text}
        </p>
      )}
      {oneAway && !feedback && (
        <p className="mb-2 animate-pop rounded-lg bg-amber-500/15 px-4 py-2 text-sm font-medium text-amber-300">
          ¡Casi! Un jugador fuera de lugar.
        </p>
      )}

      <main className="flex w-full max-w-lg flex-1 flex-col items-center gap-2">
        {/* solved banners */}
        <div className="flex w-full flex-col gap-2">
          {sortedSolved.map((sg) => (
            <ConnectionBanner
              key={sg.groupIndex}
              sg={sg}
              animate={sg.groupIndex === justRevealed}
            />
          ))}
        </div>

        {/* remaining cells */}
        {remainingCells.length > 0 && (
          <div
            className={[
              "grid w-full grid-cols-4 gap-2",
              shakeWrong ? "animate-shake" : "",
            ].join(" ")}
          >
            {remainingCells.map((cell, localIdx) => {
              const isSelected = selected.has(localIdx);
              return (
                <button
                  key={`${cell.groupIndex}-${cell.playerId}`}
                  onClick={() => toggle(localIdx)}
                  className={[
                    "relative aspect-square overflow-hidden rounded-xl border-2 transition",
                    isSelected
                      ? "border-sky-400 bg-sky-400/20 scale-105"
                      : "border-white/15 bg-transparent hover:bg-white/[0.04] hover:scale-[1.02]",
                  ].join(" ")}
                >
                  <img
                    src={cell.imageUrl ?? undefined}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                  <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent px-1 pb-1 pt-3 text-center text-[7px] font-bold leading-tight text-white/90">
                    {cell.name.split(" ").slice(-1)[0]}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        <button
          onClick={send}
          disabled={selected.size !== 4}
          className={[
            "mt-1 w-full rounded-xl py-3 text-sm font-black uppercase tracking-wide transition",
            selected.size === 4
              ? "bg-sky-500 text-slate-950 shadow-[0_0_20px_rgba(56,189,248,0.25)] hover:bg-sky-400 active:scale-[0.99]"
              : "cursor-not-allowed bg-white/10 text-white/30",
          ].join(" ")}
        >
          Enviar
        </button>
      </main>

      <footer className="pt-6 text-center text-[11px] leading-relaxed text-white/30">
        Hecho con cariño para hinchas del fútbol argentino ⚽🇦🇷
      </footer>

      <GameFooter />
    </>
  );
}
