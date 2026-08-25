export function LinkThumbnail() {
  return (
    <div className="flex w-full flex-col items-center gap-2">
      {/* silueta con ? */}
      <div className="relative flex aspect-square w-20 items-center justify-center rounded-xl bg-white/[0.06]">
        <svg viewBox="0 0 100 100" className="h-12 w-12 text-white/25">
          <circle cx="50" cy="35" r="18" fill="currentColor" />
          <ellipse cx="50" cy="80" rx="28" ry="22" fill="currentColor" />
        </svg>
        <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-sky-500 text-[10px] font-black text-white">
          ?
        </span>
      </div>

      {/* texto */}
      <p className="text-center text-[8px] font-semibold leading-tight text-white/50">
        He jugado con estos 5 jugadores,
        <br />
        ¿quién soy?
      </p>

      {/* mini row de caras */}
      <div className="flex gap-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-5 w-5 overflow-hidden rounded bg-white/10"
          />
        ))}
      </div>
    </div>
  );
}
