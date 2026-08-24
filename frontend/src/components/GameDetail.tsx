import { useState } from "react";
import type { GameMeta } from "../lib/games";
import { GameThumbnail } from "./GameThumbnail";

interface Props {
  game: GameMeta;
  onStart: () => void;
  onBack: () => void;
}

type Difficulty = "normal" | "dificil";

const DIFFICULTIES: { id: Difficulty; label: string; hint: string }[] = [
  { id: "normal", label: "Normal", hint: "Sin límite estricto de tiempo" },
  { id: "dificil", label: "Difícil", hint: "Contra el reloj" },
];

export function GameDetail({ game, onStart, onBack }: Props) {
  // solo selección visual por ahora; la lógica de dificultad viene después
  const [difficulty, setDifficulty] = useState<Difficulty>("normal");

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
          {/* ejemplo en miniatura */}
          <div className="w-full shrink-0 self-center md:w-52">
            <GameThumbnail />
          </div>

          {/* explicación + opciones */}
          <div className="flex min-w-0 flex-1 flex-col">
            <p className="text-sm leading-relaxed text-white/70">
              {game.description}
            </p>

            <div className="mt-auto pt-5">
              <p className="mb-2 text-[11px] font-bold uppercase tracking-widest text-white/40">
                Dificultad
              </p>
              <div className="flex gap-2">
                {DIFFICULTIES.map((d) => (
                  <button
                    key={d.id}
                    onClick={() => setDifficulty(d.id)}
                    title={d.hint}
                    className={[
                      "flex-1 rounded-xl border px-4 py-2.5 text-sm font-bold transition",
                      difficulty === d.id
                        ? "border-sky-400/60 bg-sky-400/15 text-sky-200"
                        : "border-white/15 text-white/70 hover:bg-white/5",
                    ].join(" ")}
                  >
                    {d.label}
                  </button>
                ))}
              </div>

              <button
                onClick={onStart}
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
