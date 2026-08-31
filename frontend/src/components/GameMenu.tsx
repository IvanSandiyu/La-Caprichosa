import type { GameMeta } from "../lib/games";
import { GAMES } from "../lib/games";
import { GameThumbnail } from "./GameThumbnail";
import { ConexionesThumbnail } from "./ConexionesThumbnail";
import { LinkThumbnail } from "./LinkThumbnail";
import { ImpostorThumbnail } from "./ImpostorThumbnail";

interface Props {
  onSelect: (gameId: string) => void;
}

export function GameMenu({ onSelect }: Props) {
  return (
    <div className="flex w-full flex-1 flex-col">
      <header className="py-10 text-center">
        <h1 className="bg-gradient-to-r from-sky-300 via-white to-amber-200 bg-clip-text text-4xl font-black tracking-tight text-transparent sm:text-5xl">
          LA CAPRICHOSA
        </h1>
        <p className="mt-2 text-sm text-white/50">
          Juegos de trivia del fútbol argentino
        </p>
      </header>

      <div className="grid w-full gap-4 sm:grid-cols-2">
        {GAMES.map((game) => (
          <GameCard key={game.id} game={game} onSelect={onSelect} />
        ))}

        {/* placeholder para juegos futuros */}
        <div className="flex min-h-[220px] flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 p-3 text-center opacity-40">
          <span className="text-2xl">🔒</span>
          <p className="mt-2 text-xs font-semibold uppercase tracking-widest text-white/40">
            Pronto más juegos
          </p>
        </div>
      </div>

      <footer className="mt-auto pt-10 text-center text-[11px] leading-relaxed text-white/30">
        Hecho con cariño para hinchas del fútbol argentino ⚽🇦🇷
      </footer>
    </div>
  );
}

function GameCard({
  game,
  onSelect,
}: {
  game: GameMeta;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      onClick={() => onSelect(game.id)}
      className="group -translate-y-0 rounded-2xl border border-white/10 bg-white/[0.04] p-3 text-left transition duration-150 hover:-translate-y-0.5 hover:border-sky-400/40 hover:bg-sky-400/[0.06]"
    >
      <div className="mb-3">
        {game.id === "conexiones" ? (
          <ConexionesThumbnail />
        ) : game.id === "futbol-link" ? (
          <LinkThumbnail />
        ) : game.id === "impostor" ? (
          <ImpostorThumbnail />
        ) : (
          <GameThumbnail />
        )}
      </div>
      <div className="flex items-baseline justify-between gap-2 px-1 pb-1">
        <h2 className="text-base font-bold text-white">{game.name}</h2>
        <span className="text-xs font-bold text-sky-300 transition group-hover:text-sky-200">
          Jugar →
        </span>
      </div>
      <p className="px-1 pb-1 text-xs leading-relaxed text-white/50">
        {game.tagline}
      </p>
    </button>
  );
}
