import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Top10Data, Top10IndexEntry } from "../../lib/api";
import { api } from "../../lib/api";
import { flagFor, normalize, todayKey } from "../../lib/format";
import { GameFooter } from "../../components/GameFooter";
import { GameHeader } from "../../components/GameHeader";
import { useGameStats } from "../../hooks/useGameStats";

interface Props {
  onExit?: () => void;
}

interface SavedState {
  date: string;
  found: number[];
  done: boolean;
}

const KEY = "top10";

function loadSaved(): SavedState | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const s: SavedState = JSON.parse(raw);
    if (s.date === todayKey()) return s;
    return null;
  } catch {
    return null;
  }
}

function saveState(state: SavedState) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* sin espacio */
  }
}

const NAME_CONNECTORS = new Set([
  "de",
  "del",
  "da",
  "di",
  "von",
  "la",
  "las",
  "los",
  "le",
  "lo",
  "van",
  "dos",
  "y",
  "e",
  "el",
]);

function titleCase(s: string): string {
  return s
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .map((w) =>
      NAME_CONNECTORS.has(w) ? w : w.charAt(0).toUpperCase() + w.slice(1),
    )
    .join(" ");
}

function displayName(name: string): string {
  const [sur, ...rest] = name.split(",");
  const full = rest.length
    ? `${rest.join(",").trim()} ${sur.trim()}`
    : sur.trim();
  return titleCase(full);
}

function tokens(s: string): string[] {
  return normalize(s)
    .split(" ")
    .filter(Boolean);
}

/** ¿El texto tipeado (o un nombre del índice) corresponde a esta respuesta? */
function guessMatches(guess: string, name: string): boolean {
  const q = tokens(guess);
  const n = tokens(name);
  if (q.length === 0) return false;
  const used: boolean[] = new Array(n.length).fill(false);
  for (const g of q) {
    let ok = false;
    for (let i = 0; i < n.length; i++) {
      if (used[i]) continue;
      // una letra sola solo cuenta si es el token completo (evita que "L" = Labruna)
      if (g.length >= 2 ? n[i] === g || n[i].startsWith(g) : n[i] === g) {
        used[i] = true;
        ok = true;
        break;
      }
    }
    if (!ok) return false;
  }
  return true;
}

/** Score para las sugerencias: 0 = arranca así, 1 = una palabra arranca así,
 *  2 = aparece en algún lado. Mismo criterio que la búsqueda del GRID. */
function scoreNorm(norm: string, q: string): number | null {
  if (!q) return null;
  if (norm.startsWith(q)) return 0;
  if (norm.split(" ").some((w) => w.startsWith(q))) return 1;
  if (norm.includes(q)) return 2;
  return null;
}

interface IndexRow {
  name: string;
  norm: string;
  country: string;
}

interface Suggestion {
  name: string;
  norm: string;
  country: string;
}

export function Top10Game({ onExit }: Props) {
  const [puzzle, setPuzzle] = useState<Top10Data | null>(null);
  const [index, setIndex] = useState<Top10IndexEntry[] | null>(null);
  const [error, setError] = useState(false);
  const [found, setFound] = useState<number[]>([]);
  const [lastAdded, setLastAdded] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [shake, setShake] = useState(false);
  const [surrendered, setSurrendered] = useState(false);
  const surrenderedRef = useRef(false);
  const boxRef = useRef<HTMLDivElement>(null);

  const gs = useGameStats("top10", todayKey());
  const saved = useMemo(() => loadSaved(), []);

  useEffect(() => {
    api
      .getTop10Index()
      .then(setIndex)
      .catch(() => setIndex([]));
    api
      .getTop10()
      .then((p) => {
        setPuzzle(p);
        // reanudar partida guardada del día (si la hubiera)
        const st = loadSaved();
        if (st && st.date === p.date) {
          setFound(st.found);
        }
      })
      .catch(() => setError(true));
  }, []);

  const answerCount = puzzle?.answers.length ?? 0;
  const solved = answerCount > 0 && found.length === answerCount;
  const done = solved || saved?.done === true;

  // cerrar las sugerencias al clickear afuera
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const indexRows = useMemo<IndexRow[]>(
    () =>
      (index ?? []).map((e) => ({
        name: e.name,
        country: e.country,
        norm: normalize(e.name),
      })),
    [index],
  );

  const suggestions = useMemo<Suggestion[]>(() => {
    const q = normalize(query.trim());
    if (!q) return [];
    const out: Suggestion[] = [];
    for (const r of indexRows) {
      if (scoreNorm(r.norm, q) === null) continue;
      // ocultar jugadores que ya se adivinaron del ranking
      if (puzzle) {
        let taken = false;
        for (const fi of found) {
          if (guessMatches(r.name, puzzle.answers[fi]?.name ?? "")) {
            taken = true;
            break;
          }
        }
        if (taken) continue;
      }
      out.push({ name: r.name, norm: r.norm, country: r.country });
    }
    out.sort(
      (a, b) =>
        (scoreNorm(a.norm, q) ?? 0) - (scoreNorm(b.norm, q) ?? 0) ||
        a.name.localeCompare(b.name),
    );
    return out.slice(0, 8);
  }, [indexRows, query, puzzle, found]);

  useEffect(() => setHighlight(0), [query]);

  useEffect(() => {
    if (!solved || surrenderedRef.current || saved?.done) return;
    gs.registerResult(true);
    saveState({ date: puzzle?.date ?? todayKey(), found: [...found], done: true });
  }, [solved, surrenderedRef, saved, puzzle, found, gs.registerResult]);

  const handleSurrender = useCallback(() => {
    if (!puzzle || done) return;
    const all = Array.from({ length: puzzle.answers.length }, (_, i) => i);
    surrenderedRef.current = true;
    setSurrendered(true);
    setFound(all);
    setLastAdded(null);
    setQuery("");
    setOpen(false);
    setOpen(false);
    gs.registerResult(false);
    saveState({ date: puzzle.date, found: [...all], done: true });
  }, [puzzle, done, gs.registerResult]);

  const reveal = useCallback(
    (idx: number) => {
      if (!puzzle || done) return;
      const next = [...found, idx].sort((a, b) => a - b);
      setFound(next);
      setLastAdded(idx);
      setQuery("");
      setOpen(false);
      saveState({ date: puzzle.date, found: next, done: false });
    },
    [puzzle, found, done],
  );

  /** Intenta un nombre contra las respuestas restantes; revela si acertó. */
  const tryGuess = useCallback(
    (name: string) => {
      if (!puzzle || done) return false;
      for (let i = 0; i < puzzle.answers.length; i++) {
        if (found.includes(i)) continue;
        if (guessMatches(name, puzzle.answers[i].name)) {
          reveal(i);
          return true;
        }
      }
      return false;
    },
    [puzzle, found, done, reveal],
  );

  const fail = useCallback(() => {
    setShake(true);
    setTimeout(() => setShake(false), 450);
  }, []);

  const submit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!puzzle || done) return;
      const q = query.trim();
      if (!q) return;
      const sug = suggestions[highlight] ?? suggestions[0];
      if (sug && tryGuess(sug.name)) return;
      if (tryGuess(q)) return;
      fail();
    },
    [puzzle, done, query, suggestions, highlight, tryGuess, fail],
  );

  if (error) {
    return (
      <div className="flex w-full flex-col items-center gap-4 pt-10">
        <p className="text-sm text-red-400">Error al cargar el top 10.</p>
        <button onClick={onExit} className="text-sm text-sky-400 underline">
          Volver
        </button>
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

  return (
    <div className="flex w-full flex-col items-center gap-4 pt-4">
      <GameHeader
        gameId="top10"
        subtitle={`Fútbol Top 10 · ${
          puzzle.methodology.metric === "goles" ? "Goles" : "Partidos"
        }`}
        onExit={onExit}
        stats={gs.stats}
      />

      {/* consigna */}
      <div className="w-full rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-center">
        <p className="text-[10px] font-bold uppercase tracking-widest text-white/40">
          Consigna del día
        </p>
        <p className="mt-1 text-base font-black text-sky-200">
          {puzzle.methodology.clue}
        </p>
        <p className="mt-1 text-[11px] text-white/50">
          La bandera es tu pista: escribí el apellido de un futbolista del ranking.
        </p>
      </div>

      {/* ranking */}
      <div className="w-full max-w-md space-y-1.5">
        {puzzle.answers.map((a, i) => {
          const isFound = found.includes(i);
          return (
            <div
              key={`${a.name}-${i}`}
              className={[
                "flex h-11 items-center overflow-hidden rounded-md border border-[#0d2a45] bg-[#031120] px-3",
                i === lastAdded ? "animate-pop" : "",
              ].join(" ")}
            >
              <span className="w-7 shrink-0 pr-2 text-right text-xs font-bold text-white/50">
                {i + 1}
              </span>
              <span className="flex w-8 shrink-0 items-center justify-center border-l border-[#0d2a45] text-sm">
                {flagFor(a.country)}
              </span>
              <span className="flex-1 truncate px-3 text-sm">
                {isFound ? (
                  <span className="font-semibold text-white">
                    {displayName(a.name)}
                  </span>
                ) : (
                  <span className="font-medium tracking-widest text-white/20">
                    •••••
                  </span>
                )}
              </span>
              <span className="shrink-0 text-right">
                {isFound ? (
                  <span className="text-sm font-bold text-amber-300">
                    {a.value}
                    <span className="ml-1 text-[9px] font-semibold uppercase text-white/40">
                      {puzzle.methodology.metric === "goles" ? "goles" : "PJ"}
                    </span>
                  </span>
                ) : (
                  <span className="text-sm font-bold text-white/20">?</span>
                )}
              </span>
            </div>
          );
        })}
      </div>

      {/* input + sugerencias */}
      {!done ? (
        <div ref={boxRef} className="relative w-full max-w-md">
          <form onSubmit={submit} className="flex w-full items-center gap-2">
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setOpen(true);
              }}
              onFocus={() => query.trim() && suggestions.length > 0 && setOpen(true)}
              onKeyDown={(e) => {
                if (e.key === "ArrowDown") {
                  e.preventDefault();
                  setOpen(true);
                  setHighlight((h) => Math.min(h + 1, Math.max(0, suggestions.length - 1)));
                } else if (e.key === "ArrowUp") {
                  e.preventDefault();
                  setHighlight((h) => Math.max(h - 1, 0));
                } else if (e.key === "Escape") {
                  setOpen(false);
                }
              }}
              placeholder="Escribí el apellido de un futbolista…"
              autoComplete="off"
              autoFocus
              className={[
                "min-w-0 flex-1 rounded-lg border border-[#0d2a45] bg-[#031120] px-3 py-2.5 text-sm text-white placeholder-white/30 outline-none transition",
                "focus:border-amber-400/60",
                shake ? "animate-shake border-red-500/70" : "",
              ].join(" ")}
            />
            <button
              type="submit"
              disabled={!query.trim()}
              title="Enviar"
              className="shrink-0 rounded-lg border-2 border-amber-400 bg-[#02070e] px-3 py-2 text-sm text-amber-300 transition hover:bg-amber-400/10 disabled:opacity-30"
            >
              ★
            </button>
          </form>

          {open && suggestions.length > 0 && (
            <ul className="absolute inset-x-0 top-full z-40 mt-1.5 max-h-64 overflow-y-auto rounded-xl border border-white/10 bg-slate-900 py-1 shadow-2xl">
              {suggestions.map((s, i) => (
                <li key={s.name}>
                  <button
                    type="button"
                    onMouseEnter={() => setHighlight(i)}
                    onClick={() => {
                      if (!tryGuess(s.name)) fail();
                    }}
                    className={[
                      "flex w-full items-center gap-2 px-3 py-2 text-left",
                      i === highlight ? "bg-sky-500/15" : "",
                    ].join(" ")}
                  >
                    <span className="text-base leading-none">
                      {flagFor(s.country)}
                    </span>
                    <span className="flex-1 truncate text-sm font-medium text-white">
                      {displayName(s.name)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          <p className="mt-1.5 text-center text-[10px] text-white/30">
            Llevás {found.length} de {answerCount}. Escribí cualquier futbolista:
            si está en el ranking se revela.
          </p>

          <button
            type="button"
            onClick={handleSurrender}
            className="mt-1.5 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs font-bold text-red-300/80 transition hover:bg-red-500/20"
            title="Abandonar y ver las respuestas del día"
          >
            Rendirse
          </button>
        </div>
      ) : (
        <div
          className={[
            "w-full max-w-md rounded-2xl px-4 py-3 text-center font-black",
            surrendered
              ? "animate-pop bg-red-500/15 text-red-300"
              : solved
                ? "animate-pop bg-emerald-500/20 text-emerald-300"
                : "bg-white/5 text-white/60",
          ].join(" ")}
        >
          {surrendered
            ? "Te rendiste. Estas eran las respuestas del Top 10."
            : solved
              ? "¡Completaste el Top 10 del día!"
              : "Top 10 del día ya jugado"}
        </div>
      )}

      {done && (
        <button
          onClick={onExit}
          className="mt-1 rounded-xl bg-white/10 px-6 py-2.5 text-sm font-bold text-white transition hover:bg-white/15"
        >
          Volver al menú
        </button>
      )}

      <GameFooter />
    </div>
  );
}