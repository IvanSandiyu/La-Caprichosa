import { useCallback, useEffect, useRef, useState } from "react";
import type { GridData, GuessCell, SearchHit } from "../lib/api";
import type { TimeMode } from "../lib/games";
import { api } from "../lib/api";
import { todayKey } from "../lib/format";

export const TIMER_SECONDS: Record<TimeMode, number | null> = {
  relax: null,
  normal: 60,
  dificil: 40,
};

export interface Placement {
  playerId: number;
  name: string;
  imageUrl: string | null;
}

export type PickPlayer = Pick<SearchHit, "player_id" | "name" | "image_url">;

export interface PendingChoice {
  player: PickPlayer;
  cells: GuessCell[];
}

export interface Stats {
  streak: number;
  best: number;
  played: number;
  wins: number;
  lastDate: string | null;
  history: Array<{ date: string; won: boolean }>;
}

export interface SavedGame {
  placements: (Placement | null)[];
  finished: boolean;
  won: boolean;
  secondsUsed: number;
  attempts: number;
  mode?: TimeMode;
  revealed?: boolean;
}

// v2: los player_ids cambiaron al regenerar el pool histórico
const GAME_KEY = (date: string) => `caprichosa:v2:${date}`;
const STATS_KEY = "caprichosa:v2:stats";

function loadStats(): Stats {
  try {
    const raw = localStorage.getItem(STATS_KEY);
    if (raw) return JSON.parse(raw) as Stats;
  } catch {
    /* corrupto: se regenera */
  }
  return { streak: 0, best: 0, played: 0, wins: 0, lastDate: null, history: [] };
}

function saveStats(s: Stats) {
  localStorage.setItem(STATS_KEY, JSON.stringify(s));
}

export function useGame(grid: GridData | null, initialMode: TimeMode = "relax") {
  const date = grid?.date ?? todayKey();

  const [placements, setPlacements] = useState<(Placement | null)[]>(Array(9).fill(null));
  const [attempts, setAttempts] = useState(0);
  const [finished, setFinished] = useState(false);
  const [won, setWon] = useState(false);
  const [mode, setMode] = useState<TimeMode>(initialMode);
  const [secondsUsed, setSecondsUsed] = useState(0);
  const [running, setRunning] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [stats, setStats] = useState<Stats>(loadStats);
  const [pendingChoice, setPendingChoice] = useState<PendingChoice | null>(null);
  const [feedback, setFeedback] = useState<{ kind: "ok" | "miss" | "info"; text: string } | null>(null);

  const restored = useRef(false);

  // restaurar partida del día
  useEffect(() => {
    if (!grid || restored.current) return;
    restored.current = true;
    try {
      const raw = localStorage.getItem(GAME_KEY(date));
      if (raw) {
        const saved = JSON.parse(raw) as SavedGame;
        if (saved.placements?.length === 9) {
          setPlacements(saved.placements);
          setAttempts(saved.attempts ?? 0);
          setSecondsUsed(saved.secondsUsed ?? 0);
          setFinished(saved.finished ?? false);
          setWon(saved.won ?? false);
          setRevealed(saved.revealed ?? false);
        }
      }
    } catch {
      /* sin partida guardada */
    }
  }, [grid, date]);

  // persistir
  useEffect(() => {
    if (!grid || !restored.current) return;
    const payload: SavedGame = { placements, finished, won, secondsUsed, attempts, mode, revealed };
    localStorage.setItem(GAME_KEY(date), JSON.stringify(payload));
  }, [grid, date, placements, finished, won, secondsUsed, attempts, mode, revealed]);

  const timeLimit = TIMER_SECONDS[mode];

  // cronómetro
  useEffect(() => {
    if (!running || finished) return;
    const id = setInterval(() => setSecondsUsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [running, finished]);

  const registerResult = useCallback(
    (didWin: boolean) => {
      setStats((prev) => {
        if (prev.lastDate === date) return prev; // ya registrada hoy
        const streak = didWin ? prev.streak + 1 : 0;
        const next: Stats = {
          streak,
          best: Math.max(prev.best, streak),
          played: prev.played + 1,
          wins: prev.wins + (didWin ? 1 : 0),
          lastDate: date,
          history: [...(prev.history ?? []), { date, won: didWin }],
        };
        saveStats(next);
        return next;
      });
    },
    [date],
  );

  // derrota por tiempo
  useEffect(() => {
    if (!timeLimit || finished || !running) return;
    if (secondsUsed >= timeLimit) {
      setRunning(false);
      setPendingChoice(null);
      setFinished(true);
      setWon(false);
      registerResult(false);
    }
  }, [secondsUsed, timeLimit, running, finished]);

  const placeAt = useCallback(
    (cell: GuessCell, player: PickPlayer) => {
      const index = cell.row * 3 + cell.col;
      const next = [...placements];
      next[index] = { playerId: player.player_id, name: player.name, imageUrl: player.image_url };
      setPlacements(next);
      setFeedback({ kind: "ok", text: `¡${player.name} entra!` });
      if (next.every(Boolean)) {
        setFinished(true);
        setWon(true);
        setRunning(false);
        registerResult(true);
      }
    },
    [placements, registerResult],
  );

  /** Envia un intento. Devuelve cómo terminó: placed | choose | miss */
  const submitGuess = useCallback(
    async (player: PickPlayer): Promise<"placed" | "choose" | "miss"> => {
      if (!finished) setRunning(true);

      const res = await api.guess(player.player_id);
      setAttempts((a) => a + 1);

      if (!res.ok) {
        setFeedback({ kind: "miss", text: `${player.name} no cumple fila ni columna.` });
        return "miss";
      }

      // descartar casillas ya ocupadas
      const freeCells = res.cells.filter((c) => placements[c.row * 3 + c.col] === null);
      if (!freeCells.length) {
        setFeedback({ kind: "miss", text: `${player.name} ya está en la grilla.` });
        return "miss";
      }

      if (freeCells.length === 1) {
        placeAt(freeCells[0], player);
        return "placed";
      }

      // sirve en varias casillas libres → el usuario elige
      setPendingChoice({ player, cells: freeCells });
      setFeedback({
        kind: "info",
        text: `${player.name} sirve en varias casillas: elegí dónde ubicarlo.`,
      });
      return "choose";
    },
    [placements, finished, placeAt],
  );

  const confirmChoice = useCallback(
    (index: number) => {
      if (!pendingChoice) return;
      const cell = pendingChoice.cells.find((c) => c.row * 3 + c.col === index);
      if (!cell) return;
      placeAt(cell, pendingChoice.player);
      setPendingChoice(null);
    },
    [pendingChoice, placeAt],
  );

  const cancelChoice = useCallback(() => {
    setPendingChoice(null);
    setFeedback(null);
  }, []);

  const onReveal = useCallback(async () => {
    if (revealed) return;
    try {
      const cells = await api.reveal();
      const next = [...placements];
      for (const c of cells) {
        const idx = c.row * 3 + c.col;
        if (next[idx] === null) {
          next[idx] = { playerId: c.player_id, name: c.name, imageUrl: c.image_url };
        }
      }
      setPlacements(next);
      setRevealed(true);
    } catch {
      /* silenciar errores de red */
    }
  }, [revealed, placements]);

  /** Rendirse: revela las respuestas, termina la partida y cuenta derrota. */
  const surrender = useCallback(async () => {
    if (finished || revealed) return;
    setRunning(false);
    setPendingChoice(null);
    try {
      const cells = await api.reveal();
      const next = [...placements];
      for (const c of cells) {
        const idx = c.row * 3 + c.col;
        if (next[idx] === null) {
          next[idx] = { playerId: c.player_id, name: c.name, imageUrl: c.image_url };
        }
      }
      setPlacements(next);
      setRevealed(true);
    } catch {
      /* si falla la revelación, no termina el juego */
    }
    setFinished(true);
    setWon(false);
    setFeedback({ kind: "miss", text: "Te rendiste. Acá están las respuestas." });
    registerResult(false);
  }, [finished, revealed, placements, registerResult]);

  const resetDay = useCallback(() => {
    localStorage.removeItem(GAME_KEY(date));
    setPlacements(Array(9).fill(null));
    setAttempts(0);
    setSecondsUsed(0);
    setFinished(false);
    setWon(false);
    setRevealed(false);
    setRunning(false);
    setPendingChoice(null);
    setFeedback(null);
  }, [date]);

  const filledCount = placements.filter(Boolean).length;

  return {
    placements,
    filledCount,
    attempts,
    finished,
    won,
    revealed,
    onReveal,
    surrender,
    mode,
    setMode,
    timeLimit,
    secondsUsed,
    stats,
    feedback,
    pendingChoice,
    submitGuess,
    confirmChoice,
    cancelChoice,
    resetDay,
  };
}
