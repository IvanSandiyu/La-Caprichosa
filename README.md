# La Caprichosa ⚽🇦🇷

Juego diario de **trivia de fútbol argentino**, pensado al estilo de
*Football Grid* / *futbol11* / *futfactos*: un puzzle nuevo cada día basado en
jugadores y clubes del fútbol de Argentina.

> ⚠️ **En desarrollo.** Proyecto en evolución constante: puede haber jugadores
> que todavía no figuren (sobre todo de épocas históricas) y errores en los
> datos o en los juegos. Si encontrás un fallo o falta un jugador, es esperable:
> lo vamos corrigiendo a medida que afinamos la base y los puzzles.

## Juegos

Hay **4 juegos**, cada uno con una consigna distinta:

| Juego | Consigna |
|-------|----------|
| **Fútbol Argentino GRID** | Completá una grilla 3×3 colocando jugadores que cumplan la condición de la fila *y* de la columna (clubes y selección). |
| **Conexiones de Fútbol** | Encontrá los 4 grupos secretos de 4 jugadores que comparten algo en común. |
| **Fútbol Link** | Adiviná el jugador misterioso a partir de 5 ex-compañeros de equipo que se revelan de a uno. |
| **El Impostor** | Dada una categoría, encontrá a los jugadores correctos sin tocar a los impostores. |

Los puzzles son **deterministas por fecha**: todos los jugadores ven el mismo
tablero/consigna cada día.

## Stack

| Capa      | Tecnología |
|-----------|------------|
| Datos     | [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) (CC0) + enriquecimiento con **Wikidata** → SQLite |
| Backend   | Python · FastAPI · SQLite · uvicorn |
| Frontend  | React 19 · Vite · TypeScript · Tailwind CSS v4 |

## Estructura del proyecto

```
backend/
├── app/
│   ├── main.py            # API FastAPI: /api/grid, /api/guess, /api/search, /api/puzzles, /api/link, /api/impostor
│   ├── grid.py            # Fútbol GRID: generación determinista diaria + validación
│   ├── puzzles.py         # Conexiones: generación de grupos diarios
│   ├── link.py            # Fútbol Link: compañeros, solapamiento de carreras, pistas
│   ├── impostor.py        # El Impostor: categorías y generación de tableros
│   ├── schemas.py         # modelos Pydantic de la API
│   ├── db.py              # conexión SQLite
│   ├── text.py            # normalización (acentos, mayúsculas)
│   └── config.py          # configuración (CORS, etc.)
├── pipeline/
│   ├── build_dataset.py        # descarga transfermarkt-datasets y arma la base SQLite
│   ├── enrich_wikidata.py      # completa historia pre-2010 vía Wikidata
│   ├── cantera_wikidata.py     # inferiores / divisiones juveniles (tabla player_youth)
│   ├── resolve_club_qids.py    # mapea clubes a QIDs de Wikidata
│   └── wikidata_history.py     # historial de carrera de los jugadores
├── tests/                  # pytest: determinismo, resolubilidad, validación
├── data/futbol_argentino.db  # base SQLite (~2 MB, generada)
├── Procfile                # comando de arranque (Render)
└── requirements.txt        # dependencias del backend
    └── pipeline/requirements.txt
```

```
frontend/
└── src/
    ├── App.tsx                 # orquestación y rutas entre menú / juegos
    ├── components/             # Board, GameMenu, GameDetail, Modals, thumbnails, GameFooter…
    ├── games/
    │   ├── grid/GridGame.tsx        # Fútbol GRID
    │   ├── conexiones/ConexionesGame.tsx
    │   ├── link/LinkGame.tsx        # Fútbol Link
    │   └── impostor/ImpostorGame.tsx # El Impostor
    ├── hooks/useGame.ts         # estado, timer y stats en localStorage
    └── lib/                     # cliente API, tipos, helpers y configuración de juegos
```

## Dependencias

**Backend** (`backend/requirements.txt`):
`fastapi`, `uvicorn`, `pydantic`

**Pipeline** (`backend/pipeline/requirements.txt`):
`pandas`, `requests`

**Frontend** (`frontend/package.json`):
- dependencias: `react`, `react-dom`, `tailwindcss`, `@tailwindcss/vite`
- dev: `vite`, `typescript`, `@vitejs/plugin-react`, `oxlint`, `@types/*`

## Cómo correr localmente

### 1. Datos (una vez, o periódicamente para actualizar)

```powershell
cd backend
pip install -r requirements.txt -r pipeline\requirements.txt
python pipeline\build_dataset.py                 # descarga y arma la base
python pipeline\build_dataset.py --skip-download # reprocesar sin re-descargar
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
npm run dev        # http://localhost:5173 (proxy /api → backend en :8000)
```

En producción, el frontend apunta al backend con la variable de entorno
`VITE_API_URL` (ver `frontend/.env.example`).

## Despliegue

- **Backend** → [Render](https://render.com): root `backend`, build
  `pip install --only-binary :all: -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **Frontend** → [Vercel](https://vercel.com): preset Vite, root `frontend`,
  con `VITE_API_URL` apuntando a la URL del backend.

## Decisiones de diseño

- **Generación determinista por fecha**: cada juego usa una semilla estable por
  día+dificultad, así todos ven el mismo puzzle y es reproducible/testeable.
- **Validación server-side**: en Fútbol GRID la validación corre en el backend,
  no se puede hacer trampa inspeccionando el bundle.
- **Datos enriquecidos con Wikidata**: la historia pre-2010 (que
  transfermarkt-datasets cubre parcialmente) se completa con Wikidata
  (incluidas las inferiores/cánteras). La cobertura depende de qué tan completa
  esté cada carrera en Wikidata.
- **Progreso en localStorage** (estilo futbol11): partida del día, racha y
  estadísticas; si recargás a mitad de juego, seguís donde estabas.

## Tests

```powershell
cd backend
python -X utf8 -m pytest tests -q
```

## Limitaciones conocidas / roadmap

- **Jugadores históricos incompletos**: la cobertura pre-2010 depende de
  Wikidata; algunos clubes tienen huecos y varios históricos no tienen foto
  (muestran silueta).
- **Fechas de disco por club no precisas**: el solapamiento de carreras en
  Fútbol Link se estima por edad (rango activo nacimiento+18 → nacimiento+37),
  ya que la base no guarda temporadas por club.
- Datos de entrada (fechas de nacimiento, eras) pueden tener placeholders o
  errores que se van depurando.
