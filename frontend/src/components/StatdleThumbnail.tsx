const CLUES = [
  { label: "Equipo", value: "Lanús", revealed: false },
  { label: "Goles", value: "24", revealed: true },
  { label: "Edad", value: "27", revealed: true },
  { label: "Nacionalidad", value: "Argentina", revealed: false },
  { label: "Debut", value: "2015", revealed: true },
  { label: "Posición", value: "Volante", revealed: false },
  { label: "P.J.", value: "132", revealed: false },
  { label: "Clubes", value: "3", revealed: false },
  { label: "Gol/part.", value: "0.18", revealed: false },
];

export function StatdleThumbnail() {
  return (
    <div className="flex w-full flex-col items-center gap-1.5">
      {/* silueta con ? */}
      <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.06]">
        <svg viewBox="0 0 100 100" className="h-5 w-5 text-white/25">
          <circle cx="50" cy="35" r="18" fill="currentColor" />
          <ellipse cx="50" cy="80" rx="28" ry="22" fill="currentColor" />
        </svg>
        <span className="absolute -right-1 -top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-sky-500 text-[8px] font-black text-white">
          ?
        </span>
      </div>

      {/* grilla 3x3 de pistas */}
      <div className="grid w-full grid-cols-3 gap-0.5">
        {CLUES.map((c, i) => (
          <div
            key={i}
            className={[
              "flex aspect-square flex-col items-center justify-center gap-px rounded border px-0.5 text-center",
              c.revealed
                ? "border-sky-500/30 bg-sky-500/[0.12]"
                : "border-white/10 bg-white/[0.05]",
            ].join(" ")}
          >
            {c.revealed ? (
              <>
                <span className="leading-none text-[5px] font-bold uppercase tracking-wide text-sky-300/70">
                  {c.label}
                </span>
                <span className="leading-none text-[7px] font-black text-white">{c.value}</span>
              </>
            ) : (
              <span className="text-[8px] font-black leading-none text-white/20">?</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}