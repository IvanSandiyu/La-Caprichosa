import type { ReactNode } from "react";

export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-2xl border border-white/10 bg-slate-900 p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">{title}</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-white/50 transition hover:bg-white/10 hover:text-white"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function HowToPlay({ onClose }: { onClose: () => void }) {
  return (
    <Modal title="Cómo jugar" onClose={onClose}>
      <div className="space-y-3 text-sm leading-relaxed text-white/80">
        <p>
          Todos los días, una grilla 3×3 con clubes de la Primera División del
          fútbol argentino y selecciones nacionales. Tu misión: completar las 9
          casillas.
        </p>
        <p>
          En cada casilla va un futbolista que cumpla <b>ambas</b>{" "}
          condiciones: la de su fila y la de su columna. Ejemplo: si la fila es{" "}
          <i>Boca Juniors</i> y la columna <i>Selección Argentina</i>, sirve
          cualquier jugador que haya firmado para Boca y sea argentino.
        </p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Valen jugadores de cualquier época que estén en nuestra base.</li>
          <li>Si un jugador sirve en varias casillas, vos elegís dónde ponerlo.</li>
          <li>Los intentos fallidos no se penalizan… salvo contra el reloj.</li>
        </ul>
        <p>
          Elegí tu modo de tiempo antes de empezar (Relax, Normal o Difícil) y
          volvé mañana para mantener tu racha. Tu progreso queda guardado en el
          navegador.
        </p>
      </div>
    </Modal>
  );
}

export interface StatsData {
  streak: number;
  best: number;
  played: number;
  wins: number;
  lastDate: string | null;
  history?: Array<{ date: string; won: boolean }>;
}

export function StatsPanel({ stats }: { stats: StatsData }) {
  const pct = stats.played ? Math.round((stats.wins / stats.played) * 100) : 0;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Racha actual", value: stats.streak },
          { label: "Mejor racha", value: stats.best },
          { label: "Partidos jugados", value: stats.played },
          { label: "% completadas", value: `${pct}%` },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-xl border border-white/10 bg-white/[0.04] p-4 text-center">
            <div className="text-2xl font-black text-sky-300">{value}</div>
            <div className="mt-1 text-xs text-white/60">{label}</div>
          </div>
        ))}
      </div>
      {stats.history && stats.history.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-widest text-white/40">Historial</p>
          <div className="flex flex-wrap gap-1">
            {stats.history.slice(-30).map((h) => (
              <span
                key={h.date}
                className={[
                  "inline-flex h-7 w-7 items-center justify-center rounded text-[10px] font-bold",
                  h.won ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/20 text-red-300",
                ].join(" ")}
                title={`${h.date}: ${h.won ? "Victoria" : "Derrota"}`}
              >
                {h.won ? "W" : "L"}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function ResultModal({
  won,
  filled,
  revealed,
  streak,
  onStats,
  onClose,
}: {
  won: boolean;
  filled: number;
  revealed: boolean;
  streak: number;
  onStats: () => void;
  onClose: () => void;
}) {
  const title = won
    ? "¡Grilla completa! 🏆"
    : revealed
      ? "Respuestas reveladas"
      : "Se acabó el tiempo";
  return (
    <Modal title={title} onClose={onClose}>
      <div className="space-y-4 text-center">
        <p className="text-sm text-white/80">
          {won
            ? `Completaste las 9 casillas. Racha: ${streak}.`
            : revealed
              ? `Completaste ${filled} de 9 casillas por tu cuenta.`
              : `Te quedaron ${9 - filled} casillas sin completar.`}
        </p>
        <button
          onClick={onStats}
          className="w-full rounded-xl bg-sky-500 py-2.5 font-semibold text-slate-950 transition hover:bg-sky-400"
        >
          Ver estadísticas
        </button>
        <button
          onClick={onClose}
          className="w-full rounded-xl border border-white/15 py-2.5 text-sm text-white/70 transition hover:bg-white/5"
        >
          Cerrar
        </button>
      </div>
    </Modal>
  );
}
