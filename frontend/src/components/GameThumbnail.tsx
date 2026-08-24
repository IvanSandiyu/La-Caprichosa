import { kitFor } from "../lib/kits";
import { Jersey } from "./Jersey";
import { Silhouette } from "./Silhouette";

interface RealPlayer {
  name: string;
  image: string;
}

// jugadores reales para el ejemplo: sirven para las casillas que ocupan
const GUILLERMO: RealPlayer = {
  name: "G. Barros Schelotto",
  image:
    "https://commons.wikimedia.org/wiki/Special:FilePath/Guillermodandounacharla.jpg?width=250",
};
const DALESSANDRO: RealPlayer = {
  name: "A. D'Alessandro",
  image:
    "https://commons.wikimedia.org/wiki/Special:FilePath/Andr%C3%A9s%20D%27Alessandro.jpg?width=250",
};

function MiniChip({ club }: { club: string }) {
  return (
    <div className="flex aspect-square items-center justify-center rounded border border-white/10 bg-white/[0.06] p-1">
      <Jersey kit={kitFor(club)} size={22} />
    </div>
  );
}

function FilledCell({ player }: { player: RealPlayer }) {
  return (
    <div className="relative aspect-square overflow-hidden rounded border border-emerald-400/50 bg-slate-800 shadow-[0_0_8px_rgba(16,185,129,0.25)]">
      <img
        src={player.image}
        alt={player.name}
        loading="lazy"
        className="absolute inset-0 h-full w-full object-cover"
        onError={(e) => {
          e.currentTarget.style.display = "none";
        }}
      />
      {/* silueta de fondo por si la imagen falla */}
      <div className="absolute inset-0 flex -z-10 items-center justify-center">
        <Silhouette className="h-3/5 w-3/5 text-white/30" />
      </div>
      <span className="absolute inset-x-0 bottom-0 truncate bg-gradient-to-t from-black/90 to-transparent px-0.5 pb-0.5 pt-2 text-center text-[7px] font-bold leading-tight text-white">
        {player.name}
      </span>
      <span className="absolute right-0.5 top-0.5 text-[9px] text-emerald-300 drop-shadow">
        ✓
      </span>
    </div>
  );
}

function EmptyCell() {
  return (
    <div className="flex aspect-square items-center justify-center rounded border border-white/10 bg-gradient-to-br from-white/[0.07] to-white/[0.02] text-[11px] text-white/20">
      +
    </div>
  );
}

export function GameThumbnail({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={[
        "grid grid-cols-3 gap-1 rounded-lg bg-black/30 p-2",
        className ?? "",
      ].join(" ")}
    >
      {/* fila 1: esquina + columnas */}
      <div className="flex aspect-square flex-col items-center justify-center rounded bg-gradient-to-br from-sky-500/15 to-transparent p-1 leading-none">
        <span className="text-[6px] font-bold uppercase tracking-widest text-sky-300/90 sm:text-[7px]">
          Fútbol
        </span>
        <span className="bg-gradient-to-r from-sky-400 to-emerald-400 bg-clip-text text-[8px] font-black uppercase tracking-widest text-transparent sm:text-[9px]">
          GRID
        </span>
      </div>
      <MiniChip club="Boca Juniors" />
      <MiniChip club="River Plate" />

      {/* fila 2 */}
      <MiniChip club="Racing Club" />
      <FilledCell player={GUILLERMO} />
      <EmptyCell />

      {/* fila 3 */}
      <MiniChip club="San Lorenzo" />
      <EmptyCell />
      <FilledCell player={DALESSANDRO} />
    </div>
  );
}
