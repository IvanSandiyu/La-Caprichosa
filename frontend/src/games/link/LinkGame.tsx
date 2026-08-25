import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Difficulty, LinkPuzzleData, LinkTeammate, SearchHit } from "../../lib/api";
import { api } from "../../lib/api";
import { todayKey } from "../../lib/format";
import { SimpleSearch } from "./SimpleSearch";
import { Silhouette } from "../../components/Silhouette";

interface Props {
  difficulty: Difficulty;
  onExit?: () => void;
}

const MAX_ATTEMPTS = 5;
const TOTAL_TEAMMATES = 5;

interface SavedLink {
  date: string;
  difficulty: Difficulty;
  won: boolean;
  revealedCount: number;
}

function loadSaved(difficulty: Difficulty): SavedLink | null {
  try {
    const raw = localStorage.getItem("futbol-link");
    if (!raw) return null;
    const s: SavedLink = JSON.parse(raw);
    if (s.date === todayKey() && s.difficulty === difficulty) return s;
    return null;
  } catch {
    return null;
  }
}

function saveResult(difficulty: Difficulty, won: boolean, revealedCount: number) {
  localStorage.setItem(
    "futbol-link",
    JSON.stringify({ date: todayKey(), difficulty, won, revealedCount }),
  );
}

/* ── card with flip animation ─────────────────────────── */

function TeammateCard({
  revealed,
  imageUrl,
  name,
  animate,
}: {
  revealed: boolean;
  imageUrl: string | null;
  name: string;
  animate: boolean;
}) {
  const [flipping, setFlipping] = useState(false);
  const wasHidden = useRef(!revealed);

  useEffect(() => {
    if (revealed && wasHidden.current && animate) {
      setFlipping(true);
      const t = setTimeout(() => setFlipping(false), 500);
      return () => clearTimeout(t);
    }
    wasHidden.current = !revealed;
  }, [revealed, animate]);

  if (!revealed && !flipping) {
    return (
      <div className="flex aspect-[3/4] w-full items-center justify-center rounded-xl border border-white/15 bg-white/[0.06]">
        <span className="text-2xl font-black text-white/20">?</span>
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col items-center gap-1">
      <div
        className={[
          "aspect-[3/4] w-full overflow-hidden rounded-xl border border-white/20 bg-slate-800",
          flipping ? "animate-flipCard" : "",
        ].join(" ")}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={name}
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
      <span className="block w-full truncate text-center text-[8px] font-bold leading-tight text-white/80">
        {name}
      </span>
    </div>
  );
}

/* ── main game ──────────────────────────────────────────── */

export function LinkGame({ difficulty, onExit }: Props) {
  const [puzzle, setPuzzle] = useState<LinkPuzzleData | null>(null);
  const [error, setError] = useState(false);
  const [revealedCount, setRevealedCount] = useState(1);
  const [attempts, setAttempts] = useState(0);
  const [selectedPlayer, setSelectedPlayer] = useState<SearchHit | null>(null);
  const [feedback, setFeedback] = useState<{ kind: "ok" | "fail"; text: string } | null>(null);
  const [gameOver, setGameOver] = useState(false);
  const [won, setWon] = useState(false);
  const [justLost, setJustLost] = useState(false);
  const searchRef = useRef<{ clear: () => void } | null>(null);

  const saved = useMemo(() => loadSaved(difficulty), [difficulty]);
  useEffect(() => {
    if (saved) {
      setGameOver(true);
      setWon(saved.won);
      setRevealedCount(saved.revealedCount ?? TOTAL_TEAMMATES);
    }
  }, [saved]);

  useEffect(() => {
    if (saved) return;
    api
      .getLinkPuzzle(difficulty)
      .then(setPuzzle)
      .catch(() => setError(true));
  }, [difficulty, saved]);

  const teammates = puzzle?.teammates ?? [];
  const allRevealed = revealedCount >= TOTAL_TEAMMATES;
  const isLastChance = allRevealed && !gameOver;

  const handleGuess = useCallback(() => {
    if (!puzzle || !selectedPlayer || gameOver) return;

    const correct = selectedPlayer.player_id === puzzle.mystery_player.id;
    // clear search
    searchRef.current?.clear();
    setSelectedPlayer(null);

    if (correct) {
      setWon(true);
      setGameOver(true);
      setFeedback({ kind: "ok", text: "¡Correcto! ¡Encontraste al jugador misterioso!" });
      saveResult(difficulty, true, revealedCount);
    } else {
      const newAttempts = attempts + 1;
      setAttempts(newAttempts);

      if (newAttempts >= MAX_ATTEMPTS) {
        setGameOver(true);
        setWon(false);
        setJustLost(true);
        setFeedback({ kind: "fail", text: "Se acabaron los intentos" });
        saveResult(difficulty, false, revealedCount);
      } else if (!allRevealed) {
        const next = Math.min(revealedCount + 1, TOTAL_TEAMMATES);
        setRevealedCount(next);
        setFeedback({ kind: "fail", text: "¡No es ese! Mirá el nuevo compañero" });
      } else {
        setFeedback({ kind: "fail", text: "¡No es ese! Intento " + newAttempts + "/" + MAX_ATTEMPTS });
      }
    }
  }, [puzzle, selectedPlayer, gameOver, attempts, difficulty, allRevealed]);

  if (error) {
    return (
      <div className="flex w-full flex-col items-center gap-4 pt-10">
        <p className="text-sm text-red-400">Error al cargar el puzzle.</p>
        <button onClick={onExit} className="text-sm text-sky-400 underline">Volver</button>
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col items-center gap-5 pt-4">
      {/* flash rojo al perder */}
      {justLost && (
        <div
          className="pointer-events-none fixed inset-0 z-50 animate-[eliminate_1.8s_ease-out_forwards]"
          style={{ backgroundColor: "rgba(239, 68, 68, 0.22)" }}
        />
      )}

      {/* header */}
      <div className="flex w-full items-center justify-between">
        <button onClick={onExit} className="text-xs font-semibold text-white/60 transition hover:text-white">
          ← Salir
        </button>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-widest text-white/40">Intentos</span>
          <div className="flex gap-1">
            {Array.from({ length: MAX_ATTEMPTS }).map((_, i) => (
              <div key={i} className={["h-2 w-2 rounded-full transition", i < attempts ? "bg-red-400" : "bg-white/15"].join(" ")} />
            ))}
          </div>
        </div>
      </div>

      {/* mystery player */}
      <div className="relative flex h-24 w-24 items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed border-white/15 bg-white/[0.04]">
        {gameOver && puzzle ? (
          <>
            {puzzle.mystery_player.image_url ? (
              <img src={puzzle.mystery_player.image_url} alt={puzzle.mystery_player.name} className="h-full w-full object-cover" />
            ) : (
              <Silhouette className="h-14 w-14 text-white/15" />
            )}
            <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent px-1 pb-1 pt-3">
              <span className="block text-center text-[9px] font-bold text-white">{puzzle.mystery_player.name}</span>
            </span>
          </>
        ) : (
          <>
            <Silhouette className="h-14 w-14 text-white/15" />
            <span className="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full bg-sky-500 text-sm font-black text-white">?</span>
          </>
        )}
      </div>

      {/* instruction */}
      <p className="text-center text-sm font-semibold text-white/60">
        {gameOver
          ? won ? "¡Ganaste!" : "Se acabaron los intentos"
          : isLastChance ? "Último intento — ¡adiviná quién es!" : "¿Podés adivinar quién es?"}
      </p>

      {/* teammates */}
      <div className="grid w-full max-w-md grid-cols-5 gap-2">
        {Array.from({ length: 5 }).map((_, i) => {
          const t = teammates[i];
          if (!t) return <div key={i} className="aspect-[3/4] rounded-xl bg-white/[0.04]" />;
          return (
            <TeammateCard
              key={i}
              revealed={i < revealedCount || gameOver}
              imageUrl={t.image_url}
              name={t.name}
              animate={!gameOver}
            />
          );
        })}
      </div>

      {/* conexiones after game over */}
      {gameOver && puzzle && (
        <div className="w-full max-w-md space-y-1.5">
          <p className="text-[10px] font-bold uppercase tracking-widest text-white/40">Conexiones</p>
          {teammates.map((t: LinkTeammate, i: number) => (
            <div key={i} className="flex items-center gap-2 rounded-lg bg-white/[0.04] px-3 py-2 text-xs text-white/70">
              <img src={t.image_url ?? undefined} alt="" className="h-6 w-6 shrink-0 rounded object-cover" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
              <span className="font-semibold text-white/90">{puzzle.mystery_player.name}</span>
              <span className="text-white/40">jugó con</span>
              <span className="font-semibold text-white/90">{t.name}</span>
              <span className="text-white/40">en</span>
              <span className="font-bold text-sky-300/80">{t.club}</span>
            </div>
          ))}
        </div>
      )}

      {/* feedback */}
      {feedback && (
        <div className={[
          "w-full max-w-md rounded-xl px-4 py-2.5 text-center text-sm font-bold",
          feedback.kind === "ok" ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/20 text-red-300",
        ].join(" ")}>
          {feedback.text}
        </div>
      )}

      {/* search + guess */}
      {!gameOver && (
        <div className="flex w-full max-w-md flex-col gap-3">
          <SimpleSearch
            ref={searchRef}
            onSelect={(p) => setSelectedPlayer(p)}
            placeholder="Escribí el nombre del jugador..."
          />
          <button
            onClick={handleGuess}
            disabled={!selectedPlayer}
            className="w-full rounded-xl bg-sky-500 px-4 py-3 text-sm font-black uppercase text-slate-950 transition hover:bg-sky-400 disabled:opacity-30"
          >
            {isLastChance ? "Último intento" : "Adivinar"}
          </button>
        </div>
      )}

      {gameOver && (
        <button onClick={onExit} className="mt-2 rounded-xl bg-white/10 px-6 py-2.5 text-sm font-bold text-white transition hover:bg-white/15">
          Volver al menú
        </button>
      )}
    </div>
  );
}
