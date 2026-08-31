export function ImpostorThumbnail() {
  return (
    <div className="flex w-full flex-col items-center gap-2">
      {/* categoría */}
      <div className="w-full rounded-lg border border-white/10 bg-white/[0.06] px-2 py-1.5 text-center">
        <span className="text-[8px] font-bold uppercase tracking-widest text-sky-300/80">
          Jugó en Boca Juniors
        </span>
      </div>

      {/* grilla de rostros, uno marcado como impostor */}
      <div className="grid w-full grid-cols-5 gap-1">
        {Array.from({ length: 10 }).map((_, i) => (
          <div
            key={i}
            className={`aspect-square overflow-hidden rounded ${
              i === 6 ? "ring-2 ring-red-500 bg-red-500/20" : "bg-white/10"
            }`}
          >
            {i === 6 && (
              <div className="flex h-full w-full items-center justify-center">
                <span className="text-lg">🕵️</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* texto */}
      <p className="text-center text-[8px] font-semibold leading-tight text-white/50">
        Uno de estos no
        <br />
        pertenece. ¿Cuál?
      </p>
    </div>
  );
}
