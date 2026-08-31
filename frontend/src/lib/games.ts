import type { Difficulty } from "./api";

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
  {
    id: "conexiones",
    name: "Conexiones de Fútbol",
    tagline: "Encontrá los 4 grupos secretos",
    description:
      "Encontrá cuatro grupos de cuatro jugadores que tengan algo en común: " +
      "misma selección, mismo club, apellido familiar, o cualquier otra conexión " +
      "que se te ocurra. Elegí cuatro y enviá. Tenés pocas chances: si te equivocás " +
      "demasiado, se acabó. ¿Podés desarmar los 4 grupos sin perder?",
  },
  {
    id: "futbol-link",
    name: "Fútbol Link",
    tagline: "¿Quién es el jugador misterioso?",
    description:
      "Te damos cinco ex-compañeros de equipo de un jugador misterioso. " +
      "Se revelan de a uno: podés intentar adivinar o pasar al siguiente. " +
      "Si acertás, ganás. Si no, perdés un intento. " +
      "Después de los cinco, tenés una última oportunidad. ¿Podés encontrarlo?",
  },
  {
    id: "impostor",
    name: "El Impostor",
    tagline: "Encontrá al que no pertenece",
    description:
      "Te damos una categoría: jugaron todos en el mismo club, en la misma selección, " +
      "nacieron el mismo año, o comparten algo en común. " +
      "En el tablero hay jugadores correctos y algunos impostores que no cumplen la categoría. " +
      "Seleccioná a todos los correctos sin tocar a ningún impostor. " +
      "En modo Normal elegís todos de una; en Uno a uno, de a uno: " +
      "un solo impostor y se terminó. Una categoría nueva cada día.",
  },
];

export function getGame(id: string): GameMeta | undefined {
  return GAMES.find((g) => g.id === id);
}

/** Modos de tiempo elegibles antes de empezar una partida. */
export type TimeMode = "relax" | "normal" | "dificil";

export const TIME_OPTIONS: { id: TimeMode; label: string; hint: string }[] = [
  { id: "relax", label: "Relax", hint: "Sin límite de tiempo" },
  { id: "normal", label: "Normal", hint: "60 segundos" },
  { id: "dificil", label: "Difícil", hint: "40 segundos" },
];

export function getTimeOption(id: TimeMode) {
  return TIME_OPTIONS.find((t) => t.id === id);
}

/** Modos de dificultad para Conexiones. */
export const DIFFICULTY_OPTIONS: { id: Difficulty; label: string; hint: string }[] = [
  { id: "facil", label: "Fácil", hint: "Conexiones más obvias" },
  { id: "normal", label: "Normal", hint: "4 errores permitidos" },
  { id: "dificil", label: "Difícil", hint: "3 errores permitidos" },
];

/** Modos de juego para Impostor. */
export type ImpostorMode = "normal" | "uno-a-uno";

export const IMPOSTOR_MODE_OPTIONS: { id: ImpostorMode; label: string; hint: string }[] = [
  { id: "normal", label: "Normal", hint: "Seleccioná todos los correctos de una" },
  { id: "uno-a-uno", label: "Uno a uno", hint: "Un impostor y perdés" },
];
