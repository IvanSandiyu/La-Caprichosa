import { kitFor } from "../lib/kits";
import { Jersey } from "./Jersey";

const GUILLERMO = { url: "https://commons.wikimedia.org/wiki/Special:FilePath/Guillermodandounacharla.jpg?width=250", name: "G. Barros Schelotto" };
const DALESSANDRO = { url: "https://commons.wikimedia.org/wiki/Special:FilePath/Andr%C3%A9s%20D%27Alessandro.jpg?width=250", name: "A. D'Alessandro" };

function MiniChip({ club }: { club: string }) {
  return (
    <div className="flex aspect-square items-center justify-center rounded border border-white/10 bg-white/[0.06] p-0.5">
      <Jersey kit={kitFor(club)} size={18} />
    </div>
  );
}

function EmptyCell() {
  return (
    <div className="flex aspect-square items-center justify-center rounded border border-white/10 bg-gradient-to-br from-white/[0.07] to-white/[0.02] text-[10px] text-white/20">
      +
    </div>
  );
}

function LabelChip({ text }: { text: string }) {
  return (
    <div className="flex aspect-square items-center justify-center rounded bg-gradient-to-br from-sky-500/15 to-transparent p-0.5 leading-none">
      <span className="text-center text-[5px] font-bold uppercase tracking-widest text-sky-300/90">
        {text}
      </span>
    </div>
  );
}

function FaceCell({ player }: { player: { url: string; name: string } }) {
  return (
    <div className="relative aspect-square overflow-hidden rounded border border-emerald-400/50 bg-slate-800">
      <img
        src={player.url}
        alt={player.name}
        loading="lazy"
        className="h-full w-full object-cover"
        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
      />
      <span className="absolute right-0.5 top-0.5 text-[8px] text-emerald-300 drop-shadow">
        ✓
      </span>
    </div>
  );
}

export function GameThumbnail({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={[
        "grid grid-cols-4 gap-1 rounded-lg bg-black/30 p-1.5",
        className ?? "",
      ].join(" ")}
    >
      {/* header row: logo + 3 column labels with jerseys */}
      <LabelChip text="Fut GRID" />
      <MiniChip club="Boca Juniors" />
      <MiniChip club="River Plate" />
      <MiniChip club="Racing Club" />

      {/* row 1 */}
      <LabelChip text="Argentina" />
      <FaceCell player={GUILLERMO} />
      <EmptyCell />
      <EmptyCell />

      {/* row 2 */}
      <LabelChip text="San Lorenzo" />
      <EmptyCell />
      <FaceCell player={DALESSANDRO} />
      <EmptyCell />

      {/* row 3 */}
      <LabelChip text="Huracán" />
      <EmptyCell />
      <EmptyCell />
      <EmptyCell />
    </div>
  );
}
