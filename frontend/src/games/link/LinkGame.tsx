import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Difficulty, LinkPuzzleData, LinkTeammate, SearchHit } from "../../lib/api";
import { api } from "../../lib/api";
import { prettyDate, todayKey } from "../../lib/format";
import { SimpleSearch } from "./SimpleSearch";
import { Silhouette } from "../../components/Silhouette";
import { GameFooter } from "../../components/GameFooter";
import { GameHeader } from "../../components/GameHeader";
import { useGameStats } from "../../hooks/useGameStats";

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
  years,
  clubs,
  showHints,
  animate,
}: {
  revealed: boolean;
  imageUrl: string | null;
  name: string;
  years?: string | null;
  clubs?: string[];
  showHints: boolean;
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
        <span className="text-lg font-black text-white/20">?</span>
      </div>
    );
  }

  const hasHints = showHints && (years != null || (clubs && clubs.length > 0));

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
      {hasHints && (
        <div className="flex w-full flex-col gap-0.5 text-center">
          {years && (
            <span className="block w-full text-[8px] font-bold leading-tight text-sky-300/80">{years}</span>
          )}
          {clubs && clubs.length > 0 && (
            <div className="flex w-full flex-col items-center gap-px">
              {clubs.map((club, i) => (
                <span key={i} className="block w-full text-[7px] font-medium leading-tight text-white/50">
                  {club}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
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
  const [showHints, setShowHints] = useState(false);
  const searchRef = useRef<{ clear: () => void } | null>(null);

  const gs = useGameStats("futbol-link", todayKey());

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

  const handleGuess = useCallback((player?: SearchHit) => {
    const target = player ?? selectedPlayer;
    if (!puzzle || !target || gameOver) return;

    const correct = target.player_id === puzzle.mystery_player.id;
    // clear search
    searchRef.current?.clear();
    setSelectedPlayer(null);

    if (correct) {
      setWon(true);
      setGameOver(true);
      setFeedback({ kind: "ok", text: "¡Correcto! ¡Encontraste al jugador misterioso!" });
      gs.registerResult(true);
      saveResult(difficulty, true, revealedCount);
    } else {
      const newAttempts = attempts + 1;
      setAttempts(newAttempts);

      if (newAttempts >= MAX_ATTEMPTS) {
        setGameOver(true);
        setWon(false);
        setJustLost(true);
        setFeedback({ kind: "fail", text: "Se acabaron los intentos" });
        gs.registerResult(false);
        saveResult(difficulty, false, revealedCount);
      } else if (!allRevealed) {
        const next = Math.min(revealedCount + 1, TOTAL_TEAMMATES);
        setRevealedCount(next);
        setFeedback({ kind: "fail", text: "¡No es ese! Mirá el nuevo compañero" });
      } else {
        setFeedback({ kind: "fail", text: "¡No es ese! Intento " + newAttempts + "/" + MAX_ATTEMPTS });
      }
    }
  }, [puzzle, selectedPlayer, gameOver, attempts, difficulty, allRevealed, gs.registerResult]);

  const handleSkip = useCallback(() => {
    if (gameOver || allRevealed) return;
    setRevealedCount((n) => Math.min(n + 1, TOTAL_TEAMMATES));
    setFeedback({ kind: "fail", text: "Saltaste. Mirá el siguiente compañero" });
  }, [gameOver, allRevealed]);

  /** Rendirse: revela el jugador misterioso, termina la partida y cuenta derrota. */
  const handleSurrender = useCallback(() => {
    if (gameOver) return;
    setRevealedCount(TOTAL_TEAMMATES);
    setGameOver(true);
    setWon(false);
    setJustLost(true);
    setFeedback({ kind: "fail", text: "Te rendiste. Este era el jugador misterioso." });
    gs.registerResult(false);
    saveResult(difficulty, false, TOTAL_TEAMMATES);
  }, [gameOver, difficulty, gs.registerResult]);

  if (error) {
    return (
      <div className="flex w-full flex-col items-center gap-4 pt-10">
        <p className="text-sm text-red-400">Error al cargar el puzzle.</p>
        <button onClick={onExit} className="text-sm text-sky-400 underline">Volver</button>
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col items-center gap-3 pt-2">
      {/* flash rojo al perder */}
      {justLost && (
        <div
          className="pointer-events-none fixed inset-0 z-50 animate-[eliminate_1.8s_ease-out_forwards]"
          style={{ backgroundColor: "rgba(239, 68, 68, 0.22)" }}
        />
      )}

      {/* header */}
      <GameHeader
        gameId="futbol-link"
        subtitle={puzzle ? `Fútbol Link · ${prettyDate(puzzle.date)}` : "Fútbol Link"}
        onExit={onExit}
        stats={gs.stats}
      />

      {/* intentos */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-bold uppercase tracking-widest text-white/40">Intentos</span>
        <div className="flex gap-1">
          {Array.from({ length: MAX_ATTEMPTS }).map((_, i) => (
            <div key={i} className={["h-1.5 w-1.5 rounded-full transition", i < attempts ? "bg-red-400" : "bg-white/15"].join(" ")} />
          ))}
        </div>
      </div>

      {/* mystery player */}
      <div className="relative flex h-16 w-16 items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-white/15 bg-white/[0.04]">
        {gameOver && puzzle ? (
          <>
            {puzzle.mystery_player.image_url ? (
              <img src={puzzle.mystery_player.image_url} alt={puzzle.mystery_player.name} className="h-full w-full object-cover" />
            ) : (
              <Silhouette className="h-10 w-10 text-white/15" />
            )}
            <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent px-1 pb-0.5 pt-2">
              <span className="block text-center text-[8px] font-bold text-white">{puzzle.mystery_player.name}</span>
            </span>
          </>
        ) : (
          <>
            <Silhouette className="h-10 w-10 text-white/15" />
            <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-sky-500 text-[10px] font-black text-white">?</span>
          </>
        )}
      </div>

      {/* instruction */}
      <p className="text-center text-xs font-semibold text-white/60">
        {gameOver
          ? won ? "¡Ganaste!" : "Se acabaron los intentos"
          : isLastChance ? "Último intento — ¡adiviná quién es!" : "¿Podés adivinar quién es?"}
      </p>

      {/* teammates */}
      <div className="flex w-full max-w-sm flex-col gap-1.5">
        {!gameOver && !isLastChance && (
          <button
            onClick={() => setShowHints((s) => !s)}
            className={[
              "self-end rounded-lg px-2.5 py-1 text-[10px] font-bold transition",
              showHints
                ? "bg-sky-500/30 text-sky-200"
                : "bg-white/10 text-white/60 hover:bg-white/15",
            ].join(" ")}
          >
            {showHints ? "Ocultar pistas" : "Ayuda"}
          </button>
        )}
        <div className="grid w-full grid-cols-5 gap-1.5">
          {Array.from({ length: 5 }).map((_, i) => {
            const t = teammates[i];
            if (!t) return <div key={i} className="aspect-[3/4] rounded-xl bg-white/[0.04]" />;
            return (
              <TeammateCard
                key={i}
                revealed={i < revealedCount || gameOver}
                imageUrl={t.image_url}
                name={t.name}
                years={t.years}
                clubs={t.clubs}
                showHints={showHints}
                animate={!gameOver}
              />
            );
          })}
        </div>
      </div>

      {/* conexiones after game over */}
      {gameOver && puzzle && (
        <div className="w-full max-w-sm space-y-1">
          <p className="text-[10px] font-bold uppercase tracking-widest text-white/40">Conexiones</p>
          {teammates.map((t: LinkTeammate, i: number) => (
            <div key={i} className="flex items-center gap-1.5 rounded-lg bg-white/[0.04] px-2.5 py-1.5 text-[11px] text-white/70">
              <img src={t.image_url ?? undefined} alt="" className="h-5 w-5 shrink-0 rounded object-cover" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
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
          "w-full max-w-sm rounded-lg px-3 py-2 text-center text-xs font-bold",
          feedback.kind === "ok" ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/20 text-red-300",
        ].join(" ")}>
          {feedback.text}
        </div>
      )}

      {/* search + guess */}
      {!gameOver && (
        <div className="flex w-full max-w-sm flex-col gap-2">
          <SimpleSearch
            ref={searchRef}
            onSelect={(p) => setSelectedPlayer(p)}
            onEnter={(p) => handleGuess(p)}
            placeholder="Escribí el nombre del jugador..."
          />
          <div className="flex w-full gap-2">
            {!allRevealed && (
              <button
                onClick={handleSkip}
                className="rounded-lg bg-white/10 px-4 py-2 text-xs font-bold text-white/70 transition hover:bg-white/15"
              >
                Saltar
              </button>
            )}
            <button
              onClick={() => handleGuess()}
              disabled={!selectedPlayer}
              className="w-full rounded-lg bg-sky-500 px-4 py-2 text-xs font-black uppercase text-slate-950 transition hover:bg-sky-400 disabled:opacity-30"
            >
              {isLastChance ? "Último intento" : "Adivinar"}
            </button>
          </div>
          <button
            onClick={handleSurrender}
            className="w-full rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-1.5 text-xs font-bold text-red-300/80 transition hover:bg-red-500/20"
            title="Abandonar y ver quién era el jugador misterioso"
          >
            Rendirse
          </button>
        </div>
      )}

      {gameOver && (
        <button onClick={onExit} className="mt-1 rounded-lg bg-white/10 px-5 py-2 text-xs font-bold text-white transition hover:bg-white/15">
          Volver al menú
        </button>
      )}

      <GameFooter />
    </div>
  );
}
