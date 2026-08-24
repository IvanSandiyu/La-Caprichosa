import { useState } from "react";
import { getGame } from "./lib/games";
import { GameMenu } from "./components/GameMenu";
import { GameDetail } from "./components/GameDetail";
import { GridGame } from "./games/grid/GridGame";

type View =
  | { name: "menu" }
  | { name: "detail"; gameId: string }
  | { name: "game"; gameId: string };

export default function App() {
  const [view, setView] = useState<View>({ name: "menu" });

  if (view.name === "detail") {
    const game = getGame(view.gameId);
    if (game) {
      return (
        <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col items-center px-4 pb-10">
          <GameDetail
            game={game}
            onStart={() => setView({ name: "game", gameId: view.gameId })}
            onBack={() => setView({ name: "menu" })}
          />
        </div>
      );
    }
  }

  if (view.name === "game") {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col items-center px-4 pb-10">
        <GridGame onExit={() => setView({ name: "menu" })} />
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col items-center px-4 pb-10">
      <GameMenu onSelect={(gameId) => setView({ name: "detail", gameId })} />
    </div>
  );
}
