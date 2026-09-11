import { useEffect, useRef, useState } from "react";
import type { FeedbackIssue, SearchHit } from "../lib/api";
import { api } from "../lib/api";
import { Modal } from "./Modals";

export interface FeedbackPlayer {
  id: number;
  name: string;
}

interface Props {
  /** id del juego (grid, futbol-link, impostor, statdle, conexiones). */
  game?: string | null;
  /** Jugadores ya visibles en la partida, para selección rápida. */
  players?: FeedbackPlayer[];
  /** Clases extra para el botón (estilo por defecto type=text). */
  className?: string;
}

const ISSUE_LABELS: Record<FeedbackIssue, string> = {
  clubes_incompletos: "Un jugador tiene clubes incompletos",
  jugador_faltante: "Falta un jugador que no está en la base",
};

export function FeedbackControl({ game, players = [], className }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title="Reportar un error de datos (clubes o jugadores faltantes)"
        className={
          className ??
          "rounded-lg border border-white/15 px-3 py-1.5 text-xs font-semibold text-white/80 transition hover:border-amber-400/40 hover:bg-amber-400/10 hover:text-amber-200"
        }
      >
        Reportar
      </button>
      {open && (
        <FeedbackModal
          game={game}
          quickPlayers={players}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}

function FeedbackModal({
  game,
  quickPlayers,
  onClose,
}: {
  game?: string | null;
  quickPlayers: FeedbackPlayer[];
  onClose: () => void;
}) {
  const [issue, setIssue] = useState<FeedbackIssue>("clubes_incompletos");
  const [name, setName] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [searching, setSearching] = useState(false);
  const [status, setStatus] = useState<"idle" | "sending" | "done">("idle");
  const [sentId, setSentId] = useState<number | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
  }, []);

  // búsqueda live de jugadores en la base (solo para "clubes incompletos")
  const triggerSearch = (value: string) => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    const q = value.trim();
    if (issue !== "clubes_incompletos" || q.length < 3) {
      setHits([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    searchTimer.current = setTimeout(() => {
      api
        .search(q)
        .then((h) => {
          setHits(h);
          setSearching(false);
        })
        .catch(() => setSearching(false));
    }, 250);
  };

  const onIssueChange = (key: FeedbackIssue) => {
    setIssue(key);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    setHits([]);
    setSearching(false);
  };

  const pick = (pid: number, pname: string) => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    setSelectedId(pid);
    setName(pname);
    setHits([]);
    setSearching(false);
  };

  const canSend =
    name.trim().length > 0 &&
    (issue === "clubes_incompletos" ? message.trim().length > 0 : true);

  const submit = async () => {
    if (!canSend || status === "sending") return;
    setStatus("sending");
    setSendError(null);
    try {
      const res = await api.postFeedback({
        issue,
        player_id: selectedId,
        player_name: name.trim(),
        game: game ?? null,
        message: message.trim(),
      });
      setSentId(res.id);
      setStatus("done");
    } catch {
      setStatus("idle");
      setSendError("No se pudo enviar el reporte. ¿Está el servidor corriendo?");
    }
  };

  return (
    <Modal title="Reportar un error de datos" onClose={onClose}>
      {status === "done" ? (
        <div className="space-y-4 text-center">
          <p className="text-sm text-emerald-300">
            ¡Gracias! Tu reporte quedó registrado
            {sentId != null ? ` (n.º ${sentId})` : ""}. Lo revisamos y
            actualizamos el perfil.
          </p>
          <button
            onClick={onClose}
            className="w-full rounded-xl bg-sky-500 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
          >
            Cerrar
          </button>
        </div>
      ) : (
        <div className="space-y-4 text-sm">
          {/* tipo de reporte */}
          <div className="space-y-2">
            {(Object.keys(ISSUE_LABELS) as FeedbackIssue[]).map((key) => (
              <label
                key={key}
                className={[
                  "flex cursor-pointer items-start gap-2 rounded-xl border p-3 transition",
                  issue === key
                    ? "border-sky-400/60 bg-sky-400/10"
                    : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]",
                ].join(" ")}
              >
                <input
                  type="radio"
                  name="issue"
                  checked={issue === key}
                  onChange={() => onIssueChange(key)}
                  className="mt-0.5 accent-sky-400"
                />
                <span className="font-semibold text-white/90">
                  {ISSUE_LABELS[key]}
                </span>
              </label>
            ))}
          </div>

          {/* selección rápida de jugadores visibles */}
          {quickPlayers.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] font-bold uppercase tracking-widest text-white/40">
                Jugadores de esta partida
              </p>
              <div className="flex flex-wrap gap-1.5">
                {quickPlayers.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => pick(p.id, p.name)}
                    className={[
                      "rounded-lg px-2 py-1 text-[11px] font-semibold transition",
                      selectedId === p.id
                        ? "bg-sky-500/30 text-sky-100"
                        : "bg-white/[0.06] text-white/70 hover:bg-white/10",
                    ].join(" ")}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* nombre del jugador */}
          <div className="space-y-1.5">
            <label className="block text-[10px] font-bold uppercase tracking-widest text-white/40">
              Jugador
            </label>
            <input
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setSelectedId(null);
                triggerSearch(e.target.value);
              }}
              placeholder={
                issue === "clubes_incompletos"
                  ? "Escribí o elegí al jugador con clubes incompletos…"
                  : "Escribí el nombre del jugador que falta…"
              }
              className="w-full rounded-xl border border-white/15 bg-white/[0.04] px-3 py-2 text-sm text-white placeholder-white/30 outline-none transition focus:border-sky-400/60"
            />
            {issue === "clubes_incompletos" && (
              <div className="max-h-36 overflow-y-auto">
                {searching && (
                  <p className="px-1 py-1 text-xs text-white/40">Buscando…</p>
                )}
                {!searching &&
                  hits.map((h) => (
                    <button
                      key={h.player_id}
                      onClick={() => pick(h.player_id, h.name)}
                      className="block w-full rounded-lg px-2 py-1.5 text-left text-xs text-white/80 transition hover:bg-white/10"
                    >
                      {h.name}
                      {h.position ? ` · ${h.position}` : ""}
                    </button>
                  ))}
              </div>
            )}
          </div>

          {/* mensaje */}
          <div className="space-y-1.5">
            <label className="block text-[10px] font-bold uppercase tracking-widest text-white/40">
              {issue === "jugador_faltante" ? "Detalle" : "¿Qué le falta?"}
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              placeholder={
                issue === "clubes_incompletos"
                  ? "Ej: jugó también en Boca (2018-2021) y San Lorenzo (2015-2018)"
                  : "Ej: falta este jugador, apareció en la base con otro nombre"
              }
              className="w-full resize-none rounded-xl border border-white/15 bg-white/[0.04] px-3 py-2 text-sm text-white placeholder-white/30 outline-none transition focus:border-sky-400/60"
            />
          </div>

          {sendError && <p className="text-xs text-red-300">{sendError}</p>}

          <button
            onClick={submit}
            disabled={!canSend || status === "sending"}
            className="w-full rounded-xl bg-sky-500 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:opacity-30"
          >
            {status === "sending" ? "Enviando…" : "Enviar reporte"}
          </button>
        </div>
      )}
    </Modal>
  );
}