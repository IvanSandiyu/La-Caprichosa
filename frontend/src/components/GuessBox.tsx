import { useEffect, useMemo, useRef, useState } from "react";
import type { IndexPlayer, SearchHit } from "../lib/api";
import { api } from "../lib/api";
import { flagFor, normalize, positionEs } from "../lib/format";
import type { PickPlayer } from "../hooks/useGame";

interface Props {
  index: IndexPlayer[];
  disabled: boolean;
  shaking: boolean;
  onSubmit: (player: PickPlayer) => void;
}

function scoreHit(normName: string, q: string): number | null {
  if (!q) return null;
  if (normName.startsWith(q)) return 0;
  if (normName.split(" ").some((w) => w.startsWith(q))) return 1;
  if (normName.includes(q)) return 2;
  return null;
}

export function GuessBox({ index, disabled, shaking, onSubmit }: Props) {
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  const results = useMemo(() => {
    const q = normalize(query);
    if (!q) return [] as SearchHit[];
    return index
      .map((p) => ({ p, s: scoreHit(normalize(p.name), q) }))
      .filter((r): r is { p: IndexPlayer; s: number } => r.s !== null)
      .sort((a, b) => a.s - b.s || a.p.name.localeCompare(b.p.name))
      .slice(0, 12)
      .map(({ p }) => ({
        player_id: p.id,
        name: p.name,
        position: p.position,
        dob: null,
        citizenship: p.citizenship,
        image_url: null,
      }));
  }, [index, query]);

  useEffect(() => setHighlight(0), [results]);

  // cerrar el dropdown al hacer click afuera
  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const submit = async (player?: SearchHit) => {
    let chosen = player ?? results[highlight];
    if (!chosen) {
      // nombre sin autocompletar: buscamos coincidencia exacta
      const exact = results.find(
        (h) => h.name.toLowerCase() === query.trim().toLowerCase(),
      );
      if (!exact) return;
      chosen = exact;
    }
    setOpen(false);
    try {
      const full = await api.getPlayer(chosen.player_id);
      onSubmit({
        player_id: full.player_id,
        name: full.name,
        image_url: full.image_url,
      });
      setQuery("");
    } catch {
      setOpen(true);
    }
  };

  return (
    <div ref={boxRef} className="relative w-full max-w-md sm:max-w-lg">
      <div className={shaking ? "animate-shake" : ""}>
        <input
          value={query}
          disabled={disabled}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => results.length && setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setOpen(true);
              setHighlight((h) => Math.min(h + 1, results.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setHighlight((h) => Math.max(h - 1, 0));
            } else if (e.key === "Enter") {
              e.preventDefault();
              void submit();
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
          placeholder={
            disabled ? "Grilla terminada" : "Ingresá el apellido de un futbolista…"
          }
          className={[
            "w-full rounded-xl border bg-white/[0.06] px-4 py-3 text-base text-white placeholder-white/30 outline-none transition",
            disabled
              ? "border-white/5 opacity-40"
              : "border-white/15 focus:border-sky-400/60 focus:bg-sky-400/5",
          ].join(" ")}
        />
      </div>

      {open && !disabled && results.length > 0 && (
        <ul className="absolute inset-x-0 top-full z-40 mt-1.5 max-h-64 overflow-y-auto rounded-xl border border-white/10 bg-slate-900 py-1 shadow-2xl">
          {results.map((h, i) => (
            <li key={h.player_id}>
              <button
                onMouseEnter={() => setHighlight(i)}
                onClick={() => void submit(h)}
                className={[
                  "flex w-full items-center gap-3 px-3 py-2 text-left",
                  i === highlight ? "bg-sky-500/15" : "",
                ].join(" ")}
              >
                <span className="text-lg">{flagFor(h.citizenship)}</span>
                <span className="flex-1 truncate text-sm font-medium text-white">
                  {h.name}
                </span>
                <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-sky-200">
                  {positionEs(h.position)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
