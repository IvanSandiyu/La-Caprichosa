import { useState } from "react";
import type { GameMeta, TimeMode } from "../lib/games";
import {
  TIME_OPTIONS,
  DIFFICULTY_OPTIONS,
  IMPOSTOR_MODE_OPTIONS,
  STATDLE_DIFFICULTY_OPTIONS,
} from "../lib/games";
import type { Difficulty } from "../lib/api";
import type { ImpostorMode } from "../lib/games";
import { GameThumbnail } from "./GameThumbnail";
import { ConexionesThumbnail } from "./ConexionesThumbnail";
import { LinkThumbnail } from "./LinkThumbnail";
import { ImpostorThumbnail } from "./ImpostorThumbnail";
import { StatdleThumbnail } from "./StatdleThumbnail";

interface Props {
  game: GameMeta;
  onStartGrid?: (timeMode: TimeMode) => void;
  onStartConexiones?: (difficulty: Difficulty) => void;
  onStartLink?: (difficulty: Difficulty) => void;
  onStartImpostor?: (difficulty: Difficulty, mode: ImpostorMode) => void;
  onStartStatdle?: (difficulty: Difficulty) => void;
  onBack: () => void;
}

export function GameDetail({ game, onStartGrid, onStartConexiones, onStartLink, onStartImpostor, onStartStatdle, onBack }: Props) {
  const isGrid = game.id === "grid";
  const isConexiones = game.id === "conexiones";
  const isLink = game.id === "futbol-link";
  const isImpostor = game.id === "impostor";
  const isStatdle = game.id === "statdle";
  const usesDifficulty = isConexiones || isLink || isImpostor || isStatdle;
  const difficultyOptions = isStatdle ? STATDLE_DIFFICULTY_OPTIONS : DIFFICULTY_OPTIONS;
  const [timeMode, setTimeMode] = useState<TimeMode>("normal");
  const [difficulty, setDifficulty] = useState<Difficulty>("normal");
  const [impostorMode, setImpostorMode] = useState<ImpostorMode>("normal");

  const handleStart = () => {
    if (isGrid && onStartGrid) onStartGrid(timeMode);
    if (isConexiones && onStartConexiones) onStartConexiones(difficulty);
    if (isLink && onStartLink) onStartLink(difficulty);
    if (isImpostor && onStartImpostor) onStartImpostor(difficulty, impostorMode);
    if (isStatdle && onStartStatdle) onStartStatdle(difficulty);
  };

  const thumb = isConexiones ? <ConexionesThumbnail /> : isLink ? <LinkThumbnail /> : isImpostor ? <ImpostorThumbnail /> : isStatdle ? <StatdleThumbnail /> : <GameThumbnail />;

  return (
    <div className="flex w-full flex-1 flex-col">
      <button
        onClick={onBack}
        className="mt-3 self-start rounded-lg border border-white/15 px-2.5 py-1 text-[11px] font-semibold text-white/80 transition hover:bg-white/5"
      >
        ← Volver al menú
      </button>

      <h1 className="mt-4 bg-gradient-to-r from-sky-300 via-white to-amber-200 bg-clip-text text-2xl font-black tracking-tight text-transparent sm:text-3xl">
        {game.name}
      </h1>
      <p className="mt-0.5 text-xs capitalize text-white/50">{game.tagline}</p>

      <section className="mt-4 w-full rounded-xl border border-white/10 bg-white/[0.04] p-3 sm:p-4">
        <div className="flex flex-col gap-3 md:flex-row md:gap-5">
          {/* thumbnail */}
          <div className="w-full shrink-0 self-center md:w-36">{thumb}</div>

          {/* explicación + opciones */}
          <div className="flex min-w-0 flex-1 flex-col">
            <p className="text-xs leading-relaxed text-white/70">
              {game.description}
            </p>

            <div className="mt-auto pt-4">
              {isGrid && (
                <>
                  <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-white/40">
                    Tiempo
                  </p>
                  <div className="flex gap-1.5">
                    {TIME_OPTIONS.map((t) => (
                      <button
                        key={t.id}
                        onClick={() => setTimeMode(t.id)}
                        title={t.hint}
                        className={[
                          "flex-1 rounded-lg border px-2 py-1.5 transition",
                          timeMode === t.id
                            ? "border-sky-400/60 bg-sky-400/15"
                            : "border-white/15 hover:bg-white/5",
                        ].join(" ")}
                      >
                        <span
                          className={[
                            "block text-xs font-bold",
                            timeMode === t.id ? "text-sky-200" : "text-white/70",
                          ].join(" ")}
                        >
                          {t.label}
                        </span>
                        <span
                          className={[
                            "mt-0.5 block text-[9px]",
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
                  <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-white/40">
                    Dificultad
                  </p>
                  <div className="flex gap-1.5">
                    {difficultyOptions.map((d) => (
                      <button
                        key={d.id}
                        onClick={() => setDifficulty(d.id)}
                        title={d.hint}
                        className={[
                          "flex-1 rounded-lg border px-2 py-1.5 transition",
                          difficulty === d.id
                            ? "border-sky-400/60 bg-sky-400/15"
                            : "border-white/15 hover:bg-white/5",
                        ].join(" ")}
                      >
                        <span
                          className={[
                            "block text-xs font-bold",
                            difficulty === d.id ? "text-sky-200" : "text-white/70",
                          ].join(" ")}
                        >
                          {d.label}
                        </span>
                        <span
                          className={[
                            "mt-0.5 block text-[9px]",
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

              {isImpostor && (
                <>
                  <p className="mb-1.5 mt-3 text-[10px] font-bold uppercase tracking-widest text-white/40">
                    Modo
                  </p>
                  <div className="flex gap-1.5">
                    {IMPOSTOR_MODE_OPTIONS.map((m) => (
                      <button
                        key={m.id}
                        onClick={() => setImpostorMode(m.id)}
                        title={m.hint}
                        className={[
                          "flex-1 rounded-lg border px-2 py-1.5 transition",
                          impostorMode === m.id
                            ? "border-sky-400/60 bg-sky-400/15"
                            : "border-white/15 hover:bg-white/5",
                        ].join(" ")}
                      >
                        <span
                          className={[
                            "block text-xs font-bold",
                            impostorMode === m.id ? "text-sky-200" : "text-white/70",
                          ].join(" ")}
                        >
                          {m.label}
                        </span>
                        <span
                          className={[
                            "mt-0.5 block text-[9px]",
                            impostorMode === m.id ? "text-sky-300/70" : "text-white/40",
                          ].join(" ")}
                        >
                          {m.hint}
                        </span>
                      </button>
                    ))}
                  </div>
                </>
              )}

              <button
                onClick={handleStart}
                className="mt-3 w-full rounded-lg bg-sky-500 px-4 py-2 text-sm font-black uppercase tracking-wide text-slate-950 shadow-[0_0_16px_rgba(56,189,248,0.25)] transition hover:bg-sky-400 active:scale-[0.99]"
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
