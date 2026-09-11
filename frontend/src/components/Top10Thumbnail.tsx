export function Top10Thumbnail({ className }: { className?: string }) {
  const ranks = [
    { n: 1, w: "100%" },
    { n: 2, w: "88%" },
    { n: 3, w: "74%" },
  ];
  return (
    <div
      aria-hidden
      className={[
        "flex w-full flex-col items-center gap-1.5 rounded-lg bg-black/30 p-2",
        className ?? "",
      ].join(" ")}
    >
      <p className="text-[7px] font-black uppercase tracking-widest text-amber-300/80">
        Top 10
      </p>
      <div className="flex w-full flex-col gap-1">
        {ranks.map((r) => (
          <div key={r.n} className="flex items-center gap-1">
            <span className="w-3 text-right text-[8px] font-bold text-white/50">
              {r.n}
            </span>
            <div
              className="h-3.5 rounded-sm bg-gradient-to-r from-sky-400/30 to-sky-500/10"
              style={{ width: r.w }}
            />
          </div>
        ))}
      </div>
      <p className="mt-0.5 text-center text-[7px] font-semibold text-white/40">
        Completá el ranking
      </p>
    </div>
  );
}