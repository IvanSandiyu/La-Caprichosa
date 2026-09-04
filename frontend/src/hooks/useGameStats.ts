import { useCallback, useState } from "react";
import type { StatsData } from "../components/Modals";

const STATS_PREFIX = "caprichosa:v2:stats:";

export interface GameStats extends StatsData {}

export function useGameStats(gameId: string, date: string) {
  const [stats, setStats] = useState<StatsData>(() => {
    try {
      const raw = localStorage.getItem(STATS_PREFIX + gameId);
      if (raw) return JSON.parse(raw) as StatsData;
    } catch {
      /* corrupto: se regenera */
    }
    return { streak: 0, best: 0, played: 0, wins: 0, lastDate: null, history: [] };
  });

  const registerResult = useCallback(
    (didWin: boolean) => {
      setStats((prev) => {
        if (prev.lastDate === date) return prev; // ya registrado hoy
        const streak = didWin ? prev.streak + 1 : 0;
        const next: StatsData = {
          streak,
          best: Math.max(prev.best, streak),
          played: prev.played + 1,
          wins: prev.wins + (didWin ? 1 : 0),
          lastDate: date,
          history: [...(prev.history ?? []), { date, won: didWin }],
        };
        try {
          localStorage.setItem(STATS_PREFIX + gameId, JSON.stringify(next));
        } catch {
          /* sin espacio */
        }
        return next;
      });
    },
    [gameId, date],
  );

  return { stats, registerResult };
}