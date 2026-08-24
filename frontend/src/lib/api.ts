export type LabelKind = "club" | "country";

export interface GridLabel {
  kind: LabelKind;
  id: string;
  name: string;
}

export interface GridData {
  date: string;
  rows: GridLabel[];
  cols: GridLabel[];
}

export interface SearchHit {
  player_id: number;
  name: string;
  position: string | null;
  dob: string | null;
  citizenship: string | null;
  image_url: string | null;
}

export interface IndexPlayer {
  id: number;
  name: string;
  position: string | null;
  citizenship: string | null;
}

export interface GuessCell {
  row: number;
  col: number;
  kind: LabelKind;
}

export interface GuessResult {
  ok: boolean;
  cells: GuessCell[];
}

async function toJson<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  getGrid: () => fetch("/api/grid").then((r) => toJson<GridData>(r)),

  getPlayerIndex: () =>
    fetch("/api/players/index").then((r) => toJson<IndexPlayer[]>(r)),

  getPlayer: (playerId: number) =>
    fetch(`/api/player/${playerId}`).then((r) => toJson<SearchHit>(r)),

  search: (q: string) =>
    fetch(`/api/search?q=${encodeURIComponent(q)}`).then((r) => toJson<SearchHit[]>(r)),

  guess: (playerId: number) =>
    fetch("/api/guess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_id: playerId }),
    }).then((r) => toJson<GuessResult>(r)),
};
