# La Caprichosa ⚽🇦🇷

Juego diario tipo *Football Grid* pero 100% fútbol argentino: completá una
grilla 3×3 colocando futbolistas que cumplan la condición **de la fila y de la
columna** (clubes de Primera División + selecciones nacionales).

## Stack

| Capa      | Tecnología |
|-----------|------------|
| Datos     | [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) (CC0) → SQLite |
| Backend   | Python 3.13 · FastAPI · SQLite |
| Frontend  | React 19 · Vite · TypeScript · Tailwind v4 |

## Estructura

```
backend/
├── app/
│   ├── main.py        # API: /api/grid, /api/guess, /api/search
│   ├── grid.py        # generación determinista diaria + validación
│   ├── db.py          # conexión SQLite
│   └── text.py        # normalización (acentos, mayúsculas)
├── pipeline/
│   └── build_dataset.py   # descarga dataset y arma data/futbol_argentino.db
├── tests/             # pytest: determinismo, resolubilidad, validación
└── data/              # futbol_argentino.db (~1.3 MB, generado)

frontend/
└── src/
    ├── App.tsx                # orquestación del juego
    ├── hooks/useGame.ts       # estado, timer, stats en localStorage
    ├── components/            # Board, SearchOverlay, Modals
    └── lib/                   # cliente API y helpers
```

## Cómo correr

### 1. Datos (una vez, o semanalmente para actualizar)

```powershell
cd backend
pip install -r requirements.txt -r pipeline\requirements.txt
python pipeline\build_dataset.py            # descarga ~218 MB y procesa
python pipeline\build_dataset.py --skip-download   # reprocesar sin re-descargar
```

### 2. Backend

```powershell
cd backend
uvicorn app.main:app --port 8000
```

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxyea /api al backend)
```

## Decisiones de diseño

- **Grilla determinista por fecha**: `random.Random("la-caprichosa-<fecha>")`
  genera la misma grilla para todos los jugadores del día. La validación es
  **server-side** (no se puede hacer trampa inspeccionando el bundle).
- **Una sola selección por grilla**: con datos de ciudadanía, las casillas
  selección×selección serían irresolubles. Cada grilla = 1 país + 5 clubes,
  muestreados ponderados por tamaño de plantel histórico.
- **Umbral adaptativo de dificultad**: cada celda debe tener suficientes
  jugadores válidos (empieza exigiendo 8+ y relaja hasta encontrar combinación).
- **Progreso en localStorage** (como futbol11): partida del día, racha y stats.
  Si recargás a mitad de juego, seguís donde estabas.

## Cómo se juega

1. Escribí el apellido de un futbolista en el cuadro de búsqueda debajo de la grilla.
2. Si cumple **fila y columna**, entra solo: si sirve para una única casilla se
   ubica automáticamente con su foto; si sirve para varias, las casillas
   válidas se resaltan y elegís vos dónde ubicarlo.
3. Si no cumple, el intento rebota y seguís buscando contra el reloj.

## Limitaciones conocidas / roadmap

- La historia pre-2010 se completa con Wikidata (SPARQL, P54 con salida
  < 2012): ~3200 jugadores extra (Barros Schelotto, Riquelme, Palermo…).
  La cobertura depende de qué tan completa está la carrera de cada
  futbolista en Wikidata; algunos clubes tienen huecos.
- Sin escudos de clubes (las fotos de jugadores sí: dataset + Wikimedia).
  Jugadores históricos sin foto pública muestran una silueta.
- Un solo nivel de dificultad (fácil/legend con umbrales distintos).
- Sin cuentas ni rankings globales.

## Tests

```powershell
cd backend
python -m pytest tests -q
```
