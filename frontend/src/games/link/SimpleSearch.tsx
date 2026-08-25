import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";
import type { IndexPlayer, SearchHit } from "../../lib/api";
import { api } from "../../lib/api";
import { normalize } from "../../lib/format";

interface Props {
  onSelect: (player: SearchHit) => void;
  placeholder?: string;
}

export interface SimpleSearchHandle {
  clear: () => void;
}

function scoreHit(normName: string, q: string): number | null {
  if (!q) return null;
  if (normName.startsWith(q)) return 0;
  if (normName.split(" ").some((w) => w.startsWith(q))) return 1;
  if (normName.includes(q)) return 2;
  return null;
}

export const SimpleSearch = forwardRef<SimpleSearchHandle, Props>(
  function SimpleSearch({ onSelect, placeholder }, ref) {
    const [query, setQuery] = useState("");
    const [highlight, setHighlight] = useState(0);
    const [open, setOpen] = useState(false);
    const [index, setIndex] = useState<IndexPlayer[]>([]);
    const boxRef = useRef<HTMLDivElement>(null);

    useImperativeHandle(ref, () => ({
      clear: () => {
        setQuery("");
        setOpen(false);
      },
    }));

    useEffect(() => {
      api.getPlayerIndex().then(setIndex).catch(() => {});
    }, []);

    const results = useMemo(() => {
      const q = normalize(query);
      if (!q) return [] as IndexPlayer[];
      return index
        .map((p) => ({ p, score: scoreHit(normalize(p.name), q) }))
        .filter((x): x is { p: IndexPlayer; score: number } => x.score !== null)
        .sort((a, b) => a.score - b.score || a.p.name.localeCompare(b.p.name))
        .slice(0, 8)
        .map((x) => x.p);
    }, [query, index]);

    useEffect(() => { setHighlight(0); }, [results.length, query]);

    useEffect(() => {
      const handler = (e: MouseEvent) => {
        if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
      };
      document.addEventListener("mousedown", handler);
      return () => document.removeEventListener("mousedown", handler);
    }, []);

    const select = (p: IndexPlayer) => {
      onSelect({ player_id: p.id, name: p.name, position: p.position, dob: null, citizenship: p.citizenship, image_url: null });
      setQuery(p.name);
      setOpen(false);
    };

    return (
      <div ref={boxRef} className="relative w-full">
        <input
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") { e.preventDefault(); setHighlight((h) => Math.min(h + 1, results.length - 1)); }
            if (e.key === "ArrowUp") { e.preventDefault(); setHighlight((h) => Math.max(h - 1, 0)); }
            if (e.key === "Enter" && results[highlight]) { e.preventDefault(); select(results[highlight]); }
          }}
          placeholder={placeholder ?? "Buscar jugador..."}
          className="w-full rounded-xl border border-white/15 bg-white/[0.06] px-4 py-3 text-sm text-white placeholder:text-white/30 focus:border-sky-400/60 focus:outline-none"
        />
        {open && results.length > 0 && (
          <div className="absolute inset-x-0 top-full z-50 mt-1 max-h-52 overflow-y-auto rounded-xl border border-white/15 bg-slate-900 shadow-xl">
            {results.map((p, i) => (
              <button
                key={p.id}
                onMouseDown={(e) => { e.preventDefault(); select(p); }}
                className={[
                  "flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition",
                  i === highlight ? "bg-sky-500/20 text-sky-200" : "text-white/80 hover:bg-white/5",
                ].join(" ")}
              >
                <span className="truncate">{p.name}</span>
                {p.position && (
                  <span className="ml-auto shrink-0 text-[10px] text-white/40">{p.position}</span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  },
);
