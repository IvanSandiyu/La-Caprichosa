import { useState } from "react";
import type { Difficulty } from "./lib/api";
import type { TimeMode, ImpostorMode } from "./lib/games";
import { getGame } from "./lib/games";
import { GameMenu } from "./components/GameMenu";
import { GameDetail } from "./components/GameDetail";
import { GridGame } from "./games/grid/GridGame";
import { ConexionesGame } from "./games/conexiones/ConexionesGame";
import { LinkGame } from "./games/link/LinkGame";
import { ImpostorGame } from "./games/impostor/ImpostorGame";
import { StatdleGameUI } from "./games/statdle/StatdleGame";

type View =
  | { name: "menu" }
  | { name: "detail"; gameId: string }
  | { name: "grid"; timeMode: TimeMode }
  | { name: "conexiones"; difficulty: Difficulty }
  | { name: "futbol-link"; difficulty: Difficulty }
  | { name: "impostor"; difficulty: Difficulty; mode: ImpostorMode }
  | { name: "statdle"; difficulty: Difficulty };

export default function App() {
  const [view, setView] = useState<View>({ name: "menu" });

  if (view.name === "detail") {
    const game = getGame(view.gameId);
    if (game) {
      return (
        <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col items-center px-4 pb-10">
          <GameDetail
            game={game}
            onStartGrid={(timeMode) =>
              setView({ name: "grid", timeMode })
            }
            onStartConexiones={(difficulty) =>
              setView({ name: "conexiones", difficulty })
            }
            onStartLink={(difficulty) =>
              setView({ name: "futbol-link", difficulty })
            }
            onStartImpostor={(difficulty, mode) =>
              setView({ name: "impostor", difficulty, mode })
            }
            onStartStatdle={(difficulty) =>
              setView({ name: "statdle", difficulty })
            }
            onBack={() => setView({ name: "menu" })}
          />
        </div>
      );
    }
  }

  if (view.name === "grid") {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col items-center px-4 pb-10">
        <GridGame
          timeMode={view.timeMode}
          onExit={() => setView({ name: "menu" })}
        />
      </div>
    );
  }

  if (view.name === "conexiones") {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col items-center px-4 pb-10">
        <ConexionesGame
          difficulty={view.difficulty}
          onExit={() => setView({ name: "menu" })}
        />
      </div>
    );
  }

  if (view.name === "futbol-link") {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col items-center px-4 pb-10">
        <LinkGame
          difficulty={view.difficulty}
          onExit={() => setView({ name: "menu" })}
        />
      </div>
    );
  }

  if (view.name === "impostor") {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col items-center px-4 pb-10">
        <ImpostorGame
          difficulty={view.difficulty}
          mode={view.mode}
          onExit={() => setView({ name: "menu" })}
        />
      </div>
    );
  }

  if (view.name === "statdle") {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col items-center px-4 pb-10">
        <StatdleGameUI
          difficulty={view.difficulty}
          onExit={() => setView({ name: "menu" })}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col items-center px-4 pb-10">
      <GameMenu onSelect={(gameId) => setView({ name: "detail", gameId })} />
    </div>
  );
}
