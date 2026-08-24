import type { Kit } from "../lib/kits";

/** Camiseta estilizada en SVG, inspirada en los kit icons de Wikipedia. */
export function Jersey({ kit, size = 26 }: { kit: Kit; size?: number }) {
  const { primary, secondary, pattern } = kit;
  const uid = `${primary}${secondary}${pattern}`.replace(/[^a-z0-9]/gi, "");

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      aria-hidden="true"
      className="drop-shadow-[0_1px_2px_rgba(0,0,0,0.45)]"
    >
      <defs>
        <clipPath id={`body-${uid}`}>
          <path d="M20 6 L26 3 Q32 9 38 3 L44 6 L58 16 L50 29 L46 25 L46 59 L18 59 L18 25 L14 29 L6 16 Z" />
        </clipPath>
      </defs>

      {/* cuerpo */}
      <path
        d="M20 6 L26 3 Q32 9 38 3 L44 6 L58 16 L50 29 L46 25 L46 59 L18 59 L18 25 L14 29 L6 16 Z"
        fill={primary}
        stroke="rgba(255,255,255,0.28)"
        strokeWidth="1.5"
      />

      {/* patrones recortados al cuerpo */}
      <g clipPath={`url(#body-${uid})`}>
        {pattern === "stripes-v" && (
          <>
            <rect x="21" y="0" width="7" height="64" fill={secondary} />
            <rect x="31" y="0" width="7" height="64" fill={secondary} />
            <rect x="41" y="0" width="7" height="64" fill={secondary} />
          </>
        )}
        {pattern === "band" && <rect x="0" y="27" width="64" height="10" fill={secondary} />}
        {pattern === "band-v" && <rect x="27" y="0" width="10" height="64" fill={secondary} />}
        {pattern === "sash" && (
          <polygon points="4,20 60,40 60,52 4,32" fill={secondary} />
        )}
        {pattern === "halves" && <rect x="32" y="0" width="32" height="64" fill={secondary} />}
        {pattern === "v" && <polygon points="17,0 47,0 32,30" fill={secondary} />}
      </g>

      {/* cuello y puños */}
      <path d="M26 3 Q32 9 38 3 L36.5 1.8 Q32 6.6 27.5 1.8 Z" fill={secondary} opacity="0.95" />
    </svg>
  );
}
