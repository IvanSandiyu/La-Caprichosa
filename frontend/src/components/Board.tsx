import type { GridData, GridLabel } from "../lib/api";
import { countryKitFor, kitFor } from "../lib/kits";
import type { Placement } from "../hooks/useGame";
import { Jersey } from "./Jersey";
import { Silhouette } from "./Silhouette";

function LabelChip({ label }: { label: GridLabel }) {
  const kit =
    label.kind === "country" ? countryKitFor(label.name) : kitFor(label.name);

  return (
    <div className="flex h-full min-h-16 flex-col items-center justify-center gap-0.5 rounded-lg border border-white/10 bg-white/[0.05] px-1 py-1.5 text-center">
      <Jersey kit={kit} size={24} />
      <span className="w-full text-[9px] font-semibold leading-tight tracking-wide text-sky-100/90 sm:text-[10px]">
        {label.name}
      </span>
    </div>
  );
}

function PlacedCell({ placement }: { placement: Placement }) {
  return (
    <>
      {/* base con silueta: visible si no hay foto o si la foto falla */}
      <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-600/70 via-slate-800 to-slate-900">
        <Silhouette className="h-[55%] w-[55%] text-white/25" />
      </div>

      {placement.imageUrl && (
        <img
          src={placement.imageUrl}
          alt={placement.name}
          loading="lazy"
          className="absolute inset-0 h-full w-full rounded-lg object-cover"
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
      )}

      {/* nombre: visible al colocar y al pasar el mouse */}
      <div className="cell-name absolute inset-0 flex items-end rounded-lg bg-gradient-to-t from-black/90 via-black/35 to-transparent p-1 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
        <span className="line-clamp-2 w-full text-center text-[9px] font-bold leading-tight text-white sm:text-[10px]">
          {placement.name}
        </span>
      </div>

      <span className="absolute right-1 top-1 text-[10px] text-emerald-300/90 drop-shadow">
        ✓
      </span>
    </>
  );
}

interface Props {
  grid: GridData;
  placements: (Placement | null)[];
  candidateIndices: number[] | null;
  onChooseCell: (index: number) => void;
}

export function Board({ grid, placements, candidateIndices, onChooseCell }: Props) {
  const choosing = candidateIndices !== null && candidateIndices.length > 0;

  return (
    <div className="grid w-full max-w-md grid-cols-[minmax(72px,0.8fr)_repeat(3,1fr)] gap-1 sm:max-w-lg sm:gap-1.5">
      {/* esquina: marca */}
      <div className="flex min-h-16 flex-col items-center justify-center text-center leading-[1.15]">
        <span className="text-[7px] font-bold uppercase tracking-[0.18em] text-sky-300/80 sm:text-[8px]">
          Fútbol
        </span>
        <span className="text-[7px] font-bold uppercase tracking-[0.18em] text-sky-300/80 sm:text-[8px]">
          Argentino
        </span>
        <span className="bg-gradient-to-r from-sky-400 to-emerald-400 bg-clip-text text-[11px] font-black uppercase tracking-widest text-transparent sm:text-xs">
          GRID
        </span>
      </div>

      {grid.cols.map((c) => (
        <LabelChip key={`c-${c.id}`} label={c} />
      ))}

      {grid.rows.map((r, i) => (
        <div key={`r-${r.id}`} className="contents">
          <LabelChip label={r} />
          {grid.cols.map((c, j) => {
            const index = i * 3 + j;
            const p = placements[index];
            const isCandidate = choosing && candidateIndices!.includes(index);
            const clickable = isCandidate && !p;
            return (
              <button
                key={index}
                disabled={!clickable}
                onClick={() => clickable && onChooseCell(index)}
                className={[
                  "group relative aspect-square overflow-hidden rounded-lg border transition-all duration-150",
                  p
                    ? "border-emerald-400/50 shadow-[0_0_12px_rgba(16,185,129,0.18)]"
                    : "border-white/10 bg-gradient-to-br from-white/[0.07] to-white/[0.02]",
                  clickable
                    ? "cursor-pointer animate-pulse border-amber-300 ring-2 ring-amber-300/80 hover:scale-[1.04]"
                    : choosing && !p
                      ? "opacity-40"
                      : "",
                ].join(" ")}
                aria-label={`Casilla ${r.name} × ${c.name}${p ? `: ${p.name}` : ""}`}
              >
                {p ? (
                  <PlacedCell placement={p} />
                ) : (
                  <span className="flex h-full w-full items-center justify-center text-white/20">
                    +
                  </span>
                )}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
