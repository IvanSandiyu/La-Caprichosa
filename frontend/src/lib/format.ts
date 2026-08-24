const POSITION_ES: Record<string, string> = {
  Goalkeeper: "ARQ",
  Defender: "DEF",
  Midfield: "MED",
  Attack: "DEL",
};

export function positionEs(position: string | null): string {
  if (!position) return "—";
  return POSITION_ES[position] ?? position;
}

const FLAGS: Record<string, string> = {
  argentina: "🇦🇷",
  uruguay: "🇺🇾",
  colombia: "🇨🇴",
  paraguay: "🇵🇾",
  chile: "🇨🇱",
  brasil: "🇧🇷",
  brazil: "🇧🇷",
  peru: "🇵🇪",
  bolivia: "🇧🇴",
  ecuador: "🇪🇨",
  venezuela: "🇻🇪",
  espana: "🇪🇸",
  italia: "🇮🇹",
  mexico: "🇲🇽",
  "estados unidos": "🇺🇸",
};

export function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

export function flagFor(country: string | null): string {
  if (!country) return "";
  return FLAGS[normalize(country)] ?? "🏳️";
}

export function todayKey(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function prettyDate(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("es-AR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
