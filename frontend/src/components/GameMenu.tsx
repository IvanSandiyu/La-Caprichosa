import type { GameMeta } from "../lib/games";
import { GAMES } from "../lib/games";
import { GameThumbnail } from "./GameThumbnail";
import { ConexionesThumbnail } from "./ConexionesThumbnail";
import { LinkThumbnail } from "./LinkThumbnail";
import { ImpostorThumbnail } from "./ImpostorThumbnail";
import { StatdleThumbnail } from "./StatdleThumbnail";

interface Props {
  onSelect: (gameId: string) => void;
}

export function GameMenu({ onSelect }: Props) {
  return (
    <div className="flex w-full flex-1 flex-col">
      <header className="py-3 text-center">
        <h1 className="bg-gradient-to-r from-sky-300 via-white to-amber-200 bg-clip-text text-2xl font-black tracking-tight text-transparent">
          LA CAPRICHOSA
        </h1>
        <p className="mt-0.5 text-[11px] text-white/50">
          Juegos de trivia del fútbol argentino
        </p>
      </header>

      <div className="grid w-full grid-cols-3 gap-2">
        {GAMES.map((game) => (
          <GameCard key={game.id} game={game} onSelect={onSelect} />
        ))}

        {/* placeholder para juegos futuros */}
        <div className="flex flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-white/10 p-2 text-center opacity-40">
          <span className="text-base leading-none">🔒</span>
          <p className="text-[9px] font-semibold uppercase tracking-widest text-white/40">
            Pronto
          </p>
        </div>
      </div>

      <footer className="mt-auto pt-6 text-center text-[10px] leading-relaxed text-white/30">
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
      className="group flex flex-col gap-1.5 rounded-xl border border-white/10 bg-white/[0.04] p-2 text-left transition duration-150 hover:border-sky-400/40 hover:bg-sky-400/[0.06]"
    >
      <div className="w-full">
        {game.id === "conexiones" ? (
          <ConexionesThumbnail />
        ) : game.id === "futbol-link" ? (
          <LinkThumbnail />
        ) : game.id === "impostor" ? (
          <ImpostorThumbnail />
        ) : game.id === "statdle" ? (
          <StatdleThumbnail />
        ) : (
          <GameThumbnail />
        )}
      </div>
      <div className="flex items-baseline justify-between gap-1 px-0.5">
        <h2 className="text-[10px] font-bold leading-tight text-white">{game.name}</h2>
        <span className="text-[8px] font-bold text-sky-300 transition group-hover:text-sky-200">
          Jugar →
        </span>
      </div>
      <p className="px-0.5 text-[8px] leading-relaxed text-white/50">{game.tagline}</p>
    </button>
  );
}