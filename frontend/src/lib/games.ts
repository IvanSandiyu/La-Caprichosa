export interface GameMeta {
  id: string;
  name: string;
  tagline: string;
  description: string;
}

export const GAMES: GameMeta[] = [
  {
    id: "grid",
    name: "Fútbol Argentino GRID",
    tagline: "La grilla diaria del fútbol argentino",
    description:
      "Nueve casillas: tres filas y tres columnas de clubes y selecciones de Argentina. " +
      "Completá cada casilla con un jugador que haya vestido ambas camisetas. " +
      "Escribí el apellido, elegí entre las sugerencias y el juego ubica al jugador solo; " +
      "si sirve para varias casillas, elegís vos. Los intentos errados rebota y te restan tiempo: " +
      "cada día una grilla nueva, ¿podés completarla antes que se acabe el reloj?",
  },
];

export function getGame(id: string): GameMeta | undefined {
  return GAMES.find((g) => g.id === id);
}
