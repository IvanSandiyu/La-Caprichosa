const SOLVED = {
  name: "ARGENTINA",
  players: [
    { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Argentina%20celebrando%20copa%20%28cropped%29.jpg", name: "Maradona" },
    { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Gabriel%20batistuta.jpg", name: "Batistuta" },
    { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Juan%20Rom%C3%A1n%20Riquelme%20-%202019.jpg", name: "Riquelme" },
    { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Mario%20Kempes%20Argentina%20v%20Spain%2019%20July%202026-036%20%28cropped%29.jpg", name: "Kempes" },
  ],
};

const CELLS = [
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Daniel%20passarella%20en%201985.jpg" },
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Di%20stefano%20argentina%20%28cropped%29.jpg" },
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Ariel%20Ortega%20%28cropped%29.jpg" },
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Caniggia%20sonriente%201988.jpg" },
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Hern%C3%A1n%20Crespo%202019.jpg" },
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Javier_Saviola.jpg" },
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Claudio_Borghi.jpg" },
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Osvaldo_Ardiles_2018.jpg" },
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Valdano.jpg" },
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/25th%20Laureus%20World%20Sports%20Awards%20-%20Red%20Carpet%20-%20Diego%20Simeone%20-%20240422%20192621-2%20%28cropped%29.jpg" },
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Gabriel%20Heinze%20en%20Newell%27s%20Old%20Boys%20%282022%29.jpg" },
  { url: "http://commons.wikimedia.org/wiki/Special:FilePath/Walter%20Samuel%20-%20Inter%20Mailand%20%281%29.jpg" },
];

export function ConexionesThumbnail() {
  return (
    <div className="flex w-full flex-col gap-1">
      {/* solved connection — BIG */}
      <div className="flex w-full items-center gap-1 overflow-hidden rounded-lg bg-amber-400 px-2 py-1.5">
        <div className="flex shrink-0 gap-1">
          {SOLVED.players.slice(0, 2).map((p) => (
            <div key={p.name} className="h-6 w-6 shrink-0 overflow-hidden rounded">
              <img src={p.url} alt="" className="h-full w-full object-cover" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
            </div>
          ))}
        </div>
        <div className="flex min-w-0 flex-1 flex-col items-center">
          <span className="truncate text-[8px] font-black uppercase leading-tight text-amber-950">
            {SOLVED.name}
          </span>
          <span className="truncate text-[6px] leading-tight text-amber-950/70">
            {SOLVED.players.map((p) => p.name).join(" · ")}
          </span>
        </div>
        <div className="flex shrink-0 gap-1">
          {SOLVED.players.slice(2, 4).map((p) => (
            <div key={p.name} className="h-6 w-6 shrink-0 overflow-hidden rounded">
              <img src={p.url} alt="" className="h-full w-full object-cover" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
            </div>
          ))}
        </div>
      </div>

      {/* 12 remaining cells — SMALL */}
      <div className="grid grid-cols-4 gap-0.5">
        {CELLS.map((p, i) => (
          <div key={i} className="aspect-square overflow-hidden rounded bg-white/10">
            <img src={p.url} alt="" className="h-full w-full object-cover" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
          </div>
        ))}
      </div>
    </div>
  );
}
