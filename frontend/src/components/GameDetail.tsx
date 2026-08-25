import { useState } from "react";
import type { GameMeta, TimeMode } from "../lib/games";
import { TIME_OPTIONS, DIFFICULTY_OPTIONS } from "../lib/games";
import type { Difficulty } from "../lib/api";
import { GameThumbnail } from "./GameThumbnail";
import { ConexionesThumbnail } from "./ConexionesThumbnail";
import { LinkThumbnail } from "./LinkThumbnail";

interface Props {
  game: GameMeta;
  onStartGrid?: (timeMode: TimeMode) => void;
  onStartConexiones?: (difficulty: Difficulty) => void;
  onStartLink?: (difficulty: Difficulty) => void;
  onBack: () => void;
}

export function GameDetail({ game, onStartGrid, onStartConexiones, onStartLink, onBack }: Props) {
  const isGrid = game.id === "grid";
  const isConexiones = game.id === "conexiones";
  const isLink = game.id === "futbol-link";
  const usesDifficulty = isConexiones || isLink;

  const [timeMode, setTimeMode] = useState<TimeMode>("normal");
  const [difficulty, setDifficulty] = useState<Difficulty>("normal");

  const handleStart = () => {
    if (isGrid && onStartGrid) onStartGrid(timeMode);
    if (isConexiones && onStartConexiones) onStartConexiones(difficulty);
    if (isLink && onStartLink) onStartLink(difficulty);
  };

  return (
    <div className="flex w-full flex-1 flex-col">
      <button
        onClick={onBack}
        className="mt-5 self-start rounded-lg border border-white/15 px-3 py-1.5 text-xs font-semibold text-white/80 transition hover:bg-white/5"
      >
        ← Volver al menú
      </button>

      <h1 className="mt-6 bg-gradient-to-r from-sky-300 via-white to-amber-200 bg-clip-text text-3xl font-black tracking-tight text-transparent sm:text-4xl">
        {game.name}
      </h1>
      <p className="mt-1 text-sm capitalize text-white/50">{game.tagline}</p>

      <section className="mt-6 w-full rounded-2xl border border-white/10 bg-white/[0.04] p-4 sm:p-5">
        <div className="flex flex-col gap-4 md:flex-row md:gap-6">
          {/* thumbnail */}
          <div className="w-full shrink-0 self-center md:w-52">
            {isConexiones ? <ConexionesThumbnail /> : isLink ? <LinkThumbnail /> : <GameThumbnail />}
          </div>

          {/* explicación + opciones */}
          <div className="flex min-w-0 flex-1 flex-col">
            <p className="text-sm leading-relaxed text-white/70">
              {game.description}
            </p>

            <div className="mt-auto pt-5">
              {isGrid && (
                <>
                  <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-white/40">
                    Tiempo
                  </p>
                  <div className="flex gap-2">
                    {TIME_OPTIONS.map((t) => (
                      <button
                        key={t.id}
                        onClick={() => setTimeMode(t.id)}
                        title={t.hint}
                        className={[
                          "flex-1 rounded-xl border px-3 py-2.5 transition",
                          timeMode === t.id
                            ? "border-sky-400/60 bg-sky-400/15"
                            : "border-white/15 hover:bg-white/5",
                        ].join(" ")}
                      >
                        <span
                          className={[
                            "block text-sm font-bold",
                            timeMode === t.id ? "text-sky-200" : "text-white/70",
                          ].join(" ")}
                        >
                          {t.label}
                        </span>
                        <span
                          className={[
                            "mt-0.5 block text-[10px]",
                            timeMode === t.id ? "text-sky-300/70" : "text-white/40",
                          ].join(" ")}
                        >
                          {t.hint}
                        </span>
                      </button>
                    ))}
                  </div>
                </>
              )}

              {usesDifficulty && (
                <>
                  <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-white/40">
                    Dificultad
                  </p>
                  <div className="flex gap-2">
                    {DIFFICULTY_OPTIONS.map((d) => (
                      <button
                        key={d.id}
                        onClick={() => setDifficulty(d.id)}
                        title={d.hint}
                        className={[
                          "flex-1 rounded-xl border px-3 py-2.5 transition",
                          difficulty === d.id
                            ? "border-sky-400/60 bg-sky-400/15"
                            : "border-white/15 hover:bg-white/5",
                        ].join(" ")}
                      >
                        <span
                          className={[
                            "block text-sm font-bold",
                            difficulty === d.id ? "text-sky-200" : "text-white/70",
                          ].join(" ")}
                        >
                          {d.label}
                        </span>
                        <span
                          className={[
                            "mt-0.5 block text-[10px]",
                            difficulty === d.id ? "text-sky-300/70" : "text-white/40",
                          ].join(" ")}
                        >
                          {d.hint}
                        </span>
                      </button>
                    ))}
                  </div>
                </>
              )}

              <button
                onClick={handleStart}
                className="mt-4 w-full rounded-xl bg-sky-500 px-5 py-3 text-base font-black uppercase tracking-wide text-slate-950 shadow-[0_0_20px_rgba(56,189,248,0.25)] transition hover:bg-sky-400 active:scale-[0.99]"
              >
                Empezar juego
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
