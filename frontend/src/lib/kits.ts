import { normalize } from "./format";

export type KitPattern =
  | "solid"
  | "stripes-v"
  | "band"
  | "band-v"
  | "sash"
  | "halves"
  | "v";

export interface Kit {
  primary: string;
  secondary: string;
  pattern: KitPattern;
}

/** Equipaciones estilizadas: colores aproximados, no oficiales. */
export const CLUB_KITS: Record<string, Kit> = {
  "boca juniors": { primary: "#10407a", secondary: "#f2c300", pattern: "band" },
  "river plate": { primary: "#f8fafc", secondary: "#d2001c", pattern: "sash" },
  "racing club": { primary: "#75aadb", secondary: "#ffffff", pattern: "stripes-v" },
  independiente: { primary: "#c8102e", secondary: "#ffffff", pattern: "solid" },
  "san lorenzo": { primary: "#12326e", secondary: "#b01c2e", pattern: "stripes-v" },
  "velez sarsfield": { primary: "#ffffff", secondary: "#1a3668", pattern: "v" },
  "estudiantes de la plata": { primary: "#d2001c", secondary: "#ffffff", pattern: "stripes-v" },
  "estudiantes de ba": { primary: "#ffffff", secondary: "#d2001c", pattern: "sash" },
  "gimnasia lp": { primary: "#ffffff", secondary: "#0a2240", pattern: "sash" },
  "gimnasia y esgrima de mendoza": { primary: "#ffffff", secondary: "#12326e", pattern: "stripes-v" },
  "newell s old boys": { primary: "#d2001c", secondary: "#141414", pattern: "halves" },
  "rosario central": { primary: "#f2c300", secondary: "#12326e", pattern: "halves" },
  talleres: { primary: "#ffffff", secondary: "#1a3668", pattern: "stripes-v" },
  belgrano: { primary: "#75aadb", secondary: "#ffffff", pattern: "stripes-v" },
  huracan: { primary: "#ffffff", secondary: "#d2001c", pattern: "band" },
  banfield: { primary: "#007a33", secondary: "#ffffff", pattern: "stripes-v" },
  lanus: { primary: "#6e1e3c", secondary: "#ffffff", pattern: "solid" },
  "argentinos juniors": { primary: "#ffffff", secondary: "#d2001c", pattern: "band-v" },
  "defensa y justicia": { primary: "#00843d", secondary: "#ffd100", pattern: "halves" },
  tigre: { primary: "#1b3a6b", secondary: "#d2001c", pattern: "solid" },
  "godoy cruz": { primary: "#ffffff", secondary: "#12326e", pattern: "stripes-v" },
  "union sf": { primary: "#d2001c", secondary: "#ffffff", pattern: "stripes-v" },
  platense: { primary: "#6b4226", secondary: "#ffffff", pattern: "stripes-v" },
  "barracas central": { primary: "#ffffff", secondary: "#d2001c", pattern: "halves" },
  "instituto cba": { primary: "#75aadb", secondary: "#ffffff", pattern: "solid" },
  "central cordoba se": { primary: "#141414", secondary: "#ffffff", pattern: "stripes-v" },
  aldosivi: { primary: "#00843d", secondary: "#ffffff", pattern: "halves" },
  "sarmiento junin": { primary: "#00693e", secondary: "#ffffff", pattern: "solid" },
  "deportivo riestra": { primary: "#ffffff", secondary: "#141414", pattern: "stripes-v" },
  "atletico tucuman": { primary: "#7fb9e3", secondary: "#ffffff", pattern: "stripes-v" },
  "san martin sj": { primary: "#00693e", secondary: "#141414", pattern: "stripes-v" },
  "indep rivadavia": { primary: "#4fa8dc", secondary: "#ffffff", pattern: "stripes-v" },
};

const FALLBACK: Kit = { primary: "#475569", secondary: "#94a3b8", pattern: "solid" };

export function kitFor(labelName: string): Kit {
  return CLUB_KITS[normalize(labelName)] ?? FALLBACK;
}

/** Camisetas de selecciones: la albiceleste y un genérico neutro. */
export const COUNTRY_KITS: Record<string, Kit> = {
  argentina: { primary: "#75aadb", secondary: "#ffffff", pattern: "stripes-v" },
  uruguay: { primary: "#7db8e8", secondary: "#ffffff", pattern: "solid" },
  brasil: { primary: "#f8d12a", secondary: "#0b6b3a", pattern: "v" },
};

const COUNTRY_FALLBACK: Kit = {
  primary: "#334155",
  secondary: "#64748b",
  pattern: "stripes-v",
};

export function countryKitFor(labelName: string): Kit {
  return COUNTRY_KITS[normalize(labelName)] ?? COUNTRY_FALLBACK;
}
