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

export interface RevealCell {
  row: number;
  col: number;
  player_id: number;
  name: string;
  image_url: string | null;
}

/* ── Conexiones ────────────────────────────────────────────── */

export type Difficulty = "facil" | "normal" | "dificil";

export interface PuzzleGroupData {
  name: string;
  group_type: string;
  player_ids: number[];
  player_names: string[];
  image_urls: (string | null)[];
}

export interface PuzzleData {
  date: string;
  difficulty: Difficulty;
  groups: PuzzleGroupData[];
  player_ids: number[];
}

/* ── Futbol Link ─────────────────────────────────────────── */

export interface LinkTeammate {
  id: number;
  name: string;
  image_url: string | null;
  club: string;
}

export interface LinkPuzzleData {
  date: string;
  difficulty: Difficulty;
  mystery_player: { id: number; name: string; image_url: string | null };
  teammates: LinkTeammate[];
}

/* ── Impostor ──────────────────────────────────────────── */

export interface ImpostorPlayer {
  id: number;
  name: string;
  image_url: string | null;
  is_impostor: boolean;
}

export interface ImpostorPuzzleData {
  date: string;
  difficulty: Difficulty;
  category: string;
  category_type: string;
  players: ImpostorPlayer[];
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

  reveal: () =>
    fetch("/api/reveal", { method: "POST" }).then((r) => toJson<RevealCell[]>(r)),

  getPuzzle: (difficulty: string) =>
    fetch(`/api/puzzles/today?difficulty=${difficulty}`).then((r) => toJson<PuzzleData>(r)),

  getLinkPuzzle: (difficulty: string) =>
    fetch(`/api/link/today?difficulty=${difficulty}`).then((r) => toJson<LinkPuzzleData>(r)),

  getImpostor: (difficulty: string) =>
    fetch(`/api/impostor/today?difficulty=${difficulty}`).then((r) => toJson<ImpostorPuzzleData>(r)),
};
