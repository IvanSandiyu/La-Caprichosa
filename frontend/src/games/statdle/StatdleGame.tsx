import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Difficulty, SearchHit, StatdlePuzzleData, StatdleSlot } from "../../lib/api";
import { api } from "../../lib/api";
import { prettyDate, todayKey } from "../../lib/format";
import { SimpleSearch } from "../link/SimpleSearch";
import { Silhouette } from "../../components/Silhouette";
import { GameHeader } from "../../components/GameHeader";
import { useGameStats } from "../../hooks/useGameStats";

interface Props {
  difficulty: Difficulty;
  onExit?: () => void;
}

const MAX_ATTEMPTS = 5;

interface SavedStatdle {
  date: string;
  difficulty: Difficulty;
  won: boolean;
  revealed: string[] | null;
  guesses: number;
}

function loadSaved(difficulty: Difficulty): SavedStatdle | null {
  try {
    const raw = localStorage.getItem("futbol-statdle");
    if (!raw) return null;
    const s = JSON.parse(raw);
    if (s.date === todayKey() && s.difficulty === difficulty) {
      return {
        date: s.date,
        difficulty,
        won: !!s.won,
        revealed: Array.isArray(s.revealed) ? s.revealed : null,
        guesses: s.guesses ?? 0,
      };
    }
    return null;
  } catch {
    return null;
  }
}

function saveResult(difficulty: Difficulty, won: boolean, revealed: string[] | null, guesses: number) {
  localStorage.setItem(
    "futbol-statdle",
    JSON.stringify({ date: todayKey(), difficulty, won, revealed, guesses }),
  );
}

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/* Orden visual de revelado de las tarjetas (estilo futbol11). */
const LAYOUT: { kind: string; title: string; group: 1 | 2 | 3 }[] = [
  { kind: "apps", title: "Apariciones", group: 1 },
  { kind: "goals", title: "Goles", group: 1 },
  { kind: "avg", title: "Gol/Part.", group: 1 },
  { kind: "position", title: "Posición", group: 2 },
  { kind: "country", title: "Nacionalidad", group: 2 },
  { kind: "age", title: "Edad", group: 3 },
  { kind: "debut", title: "Debut 1ª", group: 3 },
  { kind: "club", title: "Equipo", group: 3 },
];

function StatCard({
  title,
  revealed,
  value,
  locked,
}: {
  title: string;
  revealed: boolean;
  value: string | null;
  locked: boolean;
}) {
  return (
    <div className="relative flex h-full min-h-[72px] w-full flex-col items-center justify-center gap-0.5 overflow-hidden rounded-xl border border-white/10 bg-[#081221] px-1 text-center">
      <span className="text-[8px] font-black uppercase tracking-widest text-white/50">{title}</span>
      {locked ? (
        <span className="text-[10px] font-bold uppercase tracking-wider text-red-400/70">Bloqueada</span>
      ) : revealed ? (
        <span className="text-sm font-black leading-tight text-white">{value ?? "—"}</span>
      ) : (
        <span className="text-base font-black leading-none text-white/20">?</span>
      )}
    </div>
  );
}

export function StatdleGameUI({ difficulty, onExit }: Props) {
  const [puzzle, setPuzzle] = useState<StatdlePuzzleData | null>(null);
  const [error, setError] = useState(false);
  const [revealed, setRevealed] = useState<string[] | null>([]);
  const [guesses, setGuesses] = useState(0);
  const [selectedPlayer, setSelectedPlayer] = useState<SearchHit | null>(null);
  const [feedback, setFeedback] = useState<{ kind: "ok" | "fail"; text: string } | null>(null);
  const [gameOver, setGameOver] = useState(false);
  const [won, setWon] = useState(false);
  const searchRef = useRef<{ clear: () => void } | null>(null);

  const gs = useGameStats("statdle", todayKey());

  const saved = useMemo(() => loadSaved(difficulty), [difficulty]);
  useEffect(() => {
    if (saved) {
      setGameOver(true);
      setWon(saved.won);
      setRevealed(saved.revealed ?? null);
      setGuesses(saved.guesses ?? 0);
    }
  }, [saved]);

  useEffect(() => {
    api
      .getStatdle(difficulty)
      .then(setPuzzle)
      .catch(() => setError(true));
  }, [difficulty]);

  const slotOf = useCallback(
    (kind: string): StatdleSlot | null => puzzle?.slots.find((s) => s.kind === kind) ?? null,
    [puzzle],
  );

  /* tarjetas en orden visual, con su estado de revelado */
  const cards = useMemo(() => {
    return LAYOUT.map((l) => {
      const slot = slotOf(l.kind);
      const locked = !!slot?.locked;
      return {
        ...l,
        value: slot?.value ?? null,
        locked,
        revealed: !locked && (gameOver || (revealed !== null && revealed.includes(l.kind))),
      };
    });
  }, [slotOf, gameOver, revealed]);

  const unlockableKinds = useMemo(
    () => cards.filter((c) => !c.locked).map((c) => c.kind),
    [cards],
  );
  const allRevealed = revealed !== null && revealed.length >= unlockableKinds.length;
  const isLastChance = allRevealed && !gameOver;

  const handleGuess = useCallback(
    (player?: SearchHit) => {
      const target = player ?? selectedPlayer;
      if (!puzzle || !target || gameOver) return;
      const correct = target.player_id === puzzle.target.id;
      searchRef.current?.clear();
      setSelectedPlayer(null);

      if (correct) {
        setWon(true);
        setGameOver(true);
        setFeedback({ kind: "ok", text: "¡Correcto! Encontraste al jugador misterioso." });
        gs.registerResult(true);
        saveResult(difficulty, true, revealed, guesses + 1);
        return;
      }

      const newGuesses = guesses + 1;
      setGuesses(newGuesses);

      if (newGuesses >= MAX_ATTEMPTS) {
        setGameOver(true);
        setWon(false);
        setFeedback({ kind: "fail", text: "Se eliminó al jugador. Intentos agotados." });
        gs.registerResult(false);
        saveResult(difficulty, false, null, newGuesses);
      } else {
        const hidden = unlockableKinds.filter((k) => revealed === null || !revealed.includes(k));
        const revealedNow = shuffle(hidden).slice(0, 2);
        setRevealed((r) => (r === null ? null : [...r, ...revealedNow]));
        setFeedback({
          kind: "fail",
          text: "¡No es ese! Se revelaron " + revealedNow.length + " datos al azar (" + newGuesses + "/" + MAX_ATTEMPTS + ")",
        });
      }
    },
    [puzzle, selectedPlayer, gameOver, guesses, revealed, unlockableKinds, difficulty, gs.registerResult],
  );

  const handleSkip = useCallback(() => {
    if (gameOver || allRevealed || !puzzle) return;
    const hidden = unlockableKinds.filter((k) => revealed === null || !revealed.includes(k));
    const chosen = shuffle(hidden)[0];
    if (!chosen) return;
    setRevealed((r) => (r === null ? null : [...r, chosen]));
    setFeedback({ kind: "fail", text: "Salteaste. Se reveló un dato más." });
  }, [gameOver, allRevealed, puzzle, revealed, unlockableKinds]);

  const handleSurrender = useCallback(() => {
    if (gameOver) return;
    setGameOver(true);
    setWon(false);
    setRevealed(null);
    setFeedback({ kind: "fail", text: "Te rendiste. Este era el jugador misterioso." });
    gs.registerResult(false);
    saveResult(difficulty, false, null, guesses);
  }, [gameOver, difficulty, guesses, gs.registerResult]);

  const handleReset = useCallback(() => {
    localStorage.removeItem("futbol-statdle");
    setGameOver(false);
    setWon(false);
    setRevealed([]);
    setGuesses(0);
    setSelectedPlayer(null);
    setFeedback(null);
  }, []);

  if (error) {
    return (
      <div className="flex w-full flex-col items-center gap-4 pt-10">
        <p className="text-sm text-red-400">Error al cargar el puzzle.</p>
        <button onClick={onExit} className="text-sm text-sky-400 underline">Volver</button>
      </div>
    );
  }

  const groups: (1 | 2 | 3)[] = [1, 2, 3];

  return (
    <div className="flex w-full min-h-screen flex-col items-center gap-5 py-6 font-sans">
      {/* header */}
      <GameHeader
        gameId="statdle"
        subtitle={puzzle ? `El Statdle · ${prettyDate(puzzle.date)}` : "El Statdle"}
        onExit={onExit}
        stats={gs.stats}
      />

      {/* título */}
      <div className="text-center">
        <h1 className="text-2xl font-black italic tracking-wide text-white sm:text-3xl">
          <span className="text-[#FFC107]">LA CAPRICHOSA</span> STATDLE
        </h1>
        <p className="mt-1 text-xs font-medium text-white/70">
          Adiviná al jugador misterioso según sus estadísticas de la temporada
        </p>
      </div>

      {/* tablero */}
      <div className="flex w-full max-w-[700px] flex-col gap-3">
        <div className="flex flex-col gap-3 sm:flex-row">
          {/* tarjeta PLAYER */}
          <div className="relative flex min-h-[220px] w-full flex-col items-center justify-center gap-2 overflow-hidden rounded-2xl border border-white/10 bg-[#081221] p-4 sm:w-[40%]">
            {gameOver && puzzle ? (
              <>
                {puzzle.target.image_url ? (
                  <img src={puzzle.target.image_url} alt={puzzle.target.name} className="h-full w-full object-cover" />
                ) : (
                  <Silhouette className="h-20 w-20 text-white/25" />
                )}
                <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/95 to-transparent px-2 pb-2 pt-6">
                  <span className="block text-center text-sm font-black text-white">{puzzle.target.name}</span>
                </span>
              </>
            ) : (
              <>
                <span className="text-lg font-normal tracking-widest text-white/70">PLAYER</span>
                <span className="text-8xl font-black text-white drop-shadow-lg">?</span>
              </>
            )}
          </div>

          <div className="flex w-full flex-col gap-3 sm:w-[60%]">
            {/* liga / temporada */}
            <div className="flex h-[72px] w-full items-center justify-center rounded-2xl border border-white/10 bg-gradient-to-r from-[#1b2b44] to-[#124b61] text-center">
              <span className="px-2 text-xl font-black uppercase text-white drop-shadow-md sm:text-2xl">
                Liga Argentina{" "}
                {puzzle?.season && (
                  <span className="text-[#FFC107]">{puzzle.season}</span>
                )}
              </span>
            </div>

            {/* filas de estadísticas */}
            {groups.map((g) => (
              <div
                key={g}
                className={[
                  "grid flex-1 gap-2",
                  g === 1 ? "grid-cols-3" : g === 2 ? "grid-cols-2" : "grid-cols-3",
                ].join(" ")}
              >
                {cards
                  .filter((c) => c.group === g)
                  .map((c) => (
                    <StatCard
                      key={c.kind}
                      title={c.title}
                      revealed={c.revealed}
                      value={c.value}
                      locked={c.locked}
                    />
                  ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* feedback */}
      {feedback && (
        <div className={[
          "w-full max-w-[700px] rounded-xl px-4 py-2 text-center text-sm font-bold",
          feedback.kind === "ok"
            ? "bg-emerald-500/20 text-emerald-300"
            : gameOver && won === false ? "bg-red-500/20 text-red-300" : "bg-[#FFC107]/15 text-[#FFC107]/90",
        ].join(" ")}>
          {feedback.text}
        </div>
      )}

      {/* intentos */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-bold uppercase tracking-widest text-white/40">Intentos</span>
        <div className="flex gap-1">
          {Array.from({ length: MAX_ATTEMPTS }).map((_, i) => (
            <div
              key={i}
              className={["h-1.5 w-1.5 rounded-full transition", i < guesses ? "bg-red-400" : "bg-white/15"].join(" ")}
            />
          ))}
        </div>
      </div>

      {/* buscador */}
      {!gameOver && (
        <div className="flex w-full max-w-[700px] flex-col items-center gap-3">
          <div className="flex w-full items-center gap-2">
            <div className="flex-1">
              <SimpleSearch
                ref={searchRef}
                onSelect={(p) => setSelectedPlayer(p)}
                onEnter={(p) => handleGuess(p)}
                placeholder="Escribí el nombre del futbolista..."
                inputClassName="w-full rounded-lg bg-[#e2e6eb] px-4 py-2.5 text-sm font-medium text-gray-700 outline-none placeholder:text-gray-400 focus:ring-2 focus:ring-[#FFC107]"
              />
            </div>
            <button
              onClick={handleSkip}
              disabled={allRevealed}
              className="rounded-lg bg-white/10 px-5 py-2.5 text-sm font-bold text-white/80 transition hover:bg-white/15 disabled:opacity-30"
            >
              Skip
            </button>
          </div>
          <button
            onClick={() => handleGuess()}
            disabled={!selectedPlayer}
            className="w-full max-w-[700px] rounded-lg bg-[#FFC107] px-6 py-2.5 text-sm font-black uppercase text-black transition hover:bg-yellow-400 disabled:opacity-30"
          >
            {isLastChance ? "Último intento" : "Adivinar"}
          </button>
          <button
            onClick={handleSurrender}
            className="text-xs font-bold text-red-400/80 underline-offset-2 transition hover:text-red-300 hover:underline"
          >
            Rendirse y ver quién era
          </button>
        </div>
      )}

      {gameOver && (
        <div className="mt-1 flex flex-col items-center gap-2">
          <button onClick={onExit} className="rounded-lg bg-white/10 px-6 py-2 text-xs font-bold text-white transition hover:bg-white/15">
            Volver al menú
          </button>
          <button
            onClick={handleReset}
            className="text-xs font-bold text-sky-300 underline-offset-2 transition hover:text-sky-200 hover:underline"
          >
            Reiniciar el Statdle
          </button>
        </div>
      )}
    </div>
  );
}