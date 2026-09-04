import { useState } from "react";
import type { ReactNode } from "react";
import { Modal, StatsPanel } from "./Modals";
import type { StatsData } from "./Modals";

interface Props {
  gameId: string;
  subtitle?: string;
  onExit?: () => void;
  stats: StatsData;
}

const HOW_TO: Record<string, ReactNode> = {
  grid: (
    <>
      <p>
        Todos los días, una grilla 3×3 con clubes de la Primera División del
        fútbol argentino y selecciones nacionales. Tu misión: completar las 9
        casillas.
      </p>
      <p>
        En cada casilla va un futbolista que cumpla <b>ambas</b> condiciones: la
        de su fila y la de su columna. Ejemplo: si la fila es{" "}
        <i>Boca Juniors</i> y la columna <i>Selección Argentina</i>, sirve
        cualquier jugador que haya firmado para Boca y sea argentino.
      </p>
      <ul className="list-disc space-y-1 pl-5">
        <li>Valen jugadores de cualquier época que estén en nuestra base.</li>
        <li>Si un jugador sirve en varias casillas, vos elegís dónde ponerlo.</li>
        <li>Los intentos fallidos no se penalizan… salvo contra el reloj.</li>
      </ul>
    </>
  ),
  conexiones: (
    <>
      <p>
        Hay 16 futbolistas y entre ellos se esconden <b>4 conexiones</b> de 4
        jugadores cada una (ej: jugaron en el mismo club, fueron de la misma
        selección…).
      </p>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          Seleccioná 4 jugadores que creas que comparten conexión y enviá.
        </li>
        <li>
          Si forman un grupo, se bloquea y se revela el nombre de la conexión.
        </li>
        <li>Ojo con los errores: tenés un límite según la dificultad.</li>
      </ul>
    </>
  ),
  "futbol-link": (
    <>
      <p>
        Cada día hay un <b>jugador misterioso</b> de la Primera División. Se
        muestran 5 compañeros con los que compartió plantel en su carrera.
      </p>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          Escribí quién creés que es. Si fallás, se revela un compañero más.
        </li>
        <li>
          Usá "Ayuda" para ver los años y los clubes en común de cada compañero.
        </li>
        <li>Tenés 5 intentos. ¿Podés descubrir al misterioso?</li>
      </ul>
    </>
  ),
  impostor: (
    <>
      <p>
        Una categoría (ej: <i>“Jugó en Boca Juniors”</i>) con un grupo de
        futbolistas… pero <b>uno no pertenece</b>: es el impostor.
      </p>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          <b>Normal:</b> seleccioná a todos los que cumplen la categoría y
          confirmá. Si tocaste al impostor, perdés.
        </li>
        <li>
          <b>Uno a uno:</b> tocá un jugador para confirmarlo. Si tocás al
          impostor, perdés.
        </li>
      </ul>
    </>
  ),
  statdle: (
    <>
      <p>
        Adiviná al <b>jugador misterioso</b> según sus estadísticas de la
        temporada en la Primera División.
      </p>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          Por cada intento fallido se revelan <b>2 datos al azar</b> (apariciones,
          goles, posición, edad…).
        </li>
        <li>
          "Skip" revela 1 dato sin gastar intento. Tenés 5 intentos.
        </li>
        <li>Rendirte revela todo y muestra quién era el misterioso.</li>
      </ul>
    </>
  ),
};

export function GameHeader({ gameId, subtitle, onExit, stats }: Props) {
  const [modal, setModal] = useState<"howto" | "stats" | null>(null);

  return (
    <>
      <header className="flex w-full items-center justify-between border-b border-white/5 py-5">
        <div>
          <h1
            onClick={onExit}
            title={onExit ? "Volver al menú" : undefined}
            className={[
              "bg-gradient-to-r from-sky-300 via-white to-amber-200 bg-clip-text text-2xl font-black tracking-tight text-transparent",
              onExit ? "cursor-pointer transition hover:from-sky-200 hover:to-amber-100" : "",
            ].join(" ")}
          >
            LA CAPRICHOSA
          </h1>
          {subtitle && (
            <p className="text-xs capitalize text-white/50">{subtitle}</p>
          )}
        </div>
        <div className="flex gap-2">
          {onExit && (
            <button
              onClick={onExit}
              className="rounded-lg border border-white/15 px-3 py-1.5 text-xs font-semibold text-white/80 transition hover:bg-white/5"
            >
              ← Menú
            </button>
          )}
          <button
            onClick={() => setModal("howto")}
            className="rounded-lg border border-white/15 px-3 py-1.5 text-xs font-semibold text-white/80 transition hover:bg-white/5"
          >
            Cómo jugar
          </button>
          <button
            onClick={() => setModal("stats")}
            className="rounded-lg border border-white/15 px-3 py-1.5 text-xs font-semibold text-white/80 transition hover:bg-white/5"
          >
            Stats
          </button>
        </div>
      </header>

      {modal === "howto" && (
        <Modal title="Cómo jugar" onClose={() => setModal(null)}>
          <div className="space-y-3 text-sm leading-relaxed text-white/80">
            {HOW_TO[gameId] ?? <p>Aprendé jugando.</p>}
          </div>
        </Modal>
      )}

      {modal === "stats" && (
        <Modal title="Tus estadísticas" onClose={() => setModal(null)}>
          <StatsPanel stats={stats} />
        </Modal>
      )}
    </>
  );
}