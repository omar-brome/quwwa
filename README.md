# Quwwa — قوة

<p align="center">
  <img src="docs/demo.gif" width="300" alt="Logging a workout in Quwwa" />
</p>
<p align="center">
  <em>Log a set in under five taps — <a href="docs/demo.mp4">full demo video</a></em>
</p>

A mobile-first gym tracker with an AI coach. Two layers, deliberately separate:

- **Logging layer** — dumb and fast. Start a session, pick an exercise, log weight × reps
  (RPE optional), finish. Survives browser refreshes mid-session.
- **Coaching layer** — Claude reads your history and tells you what to do next and why:
  next-session plans, plateau detection, weekly reviews, and deload checks.

**Stack:** React 18 + TypeScript + Vite + Tailwind, TanStack Query, Zustand ·
FastAPI + SQLAlchemy 2.0 (async) + Alembic · PostgreSQL (SQLite fallback for dev) ·
Anthropic Claude API · Docker Compose.

## Screens

| AI session plan | Weekly review | Volume vs targets | Exercise picker |
| :---: | :---: | :---: | :---: |
| ![Coaching](docs/screenshots/01-home-coaching.png) | ![Weekly review](docs/screenshots/02-weekly-review.png) | ![Volume](docs/screenshots/03-volume-history.png) | ![Picker](docs/screenshots/04-picker.png) |

| Set logging | Session summary | Plateau detection | Profile |
| :---: | :---: | :---: | :---: |
| ![Logging](docs/screenshots/05-logging.png) | ![Summary](docs/screenshots/06-session-summary.png) | ![Plateau](docs/screenshots/07-exercise-plateau.png) | ![Profile](docs/screenshots/08-profile.png) |

> Screens show demo data from `backend/scripts/seed_demo.py` (run it to explore the app
> with realistic history; `--clean` wipes it). Assets are reproducible via
> `frontend/scripts/record-demo.mjs`.

---

## Quickstart

### 1. Configure

```sh
cp .env.example .env          # add your ANTHROPIC_API_KEY
```

Without a key everything works except AI coaching (the UI shows how to enable it).

### 2a. Run with Docker (Postgres, as intended)

```sh
docker compose up -d db backend       # db + API on :8000 (runs migrations)
cd frontend && npm install && npm run dev   # UI on :5173
```

Or everything in containers: `docker compose --profile full up`.

### 2b. Run fully local (zero-setup SQLite)

```sh
cd backend
python -m venv .venv && .venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m uvicorn app.main:app --port 8000   # SQLite + auto-seed

cd ../frontend
npm install && npm run dev
```

To point a local backend at the compose Postgres instead, set
`DATABASE_URL=postgresql+asyncpg://quwwa:quwwa@localhost:5433/quwwa` (copy
`backend/.env.example` → `backend/.env`) and run `alembic upgrade head` once.

Open http://localhost:5173 (best viewed in a mobile viewport — it's designed for the phone
you take to the gym).

### Environment variables

| Variable            | Default                          | Notes                                        |
| ------------------- | -------------------------------- | -------------------------------------------- |
| `DATABASE_URL`      | `sqlite+aiosqlite:///./quwwa.db` | Compose sets the Postgres URL                |
| `ANTHROPIC_API_KEY` | _(empty)_                        | Required for AI coaching                     |
| `ANTHROPIC_MODEL`   | `claude-sonnet-4-6`              | Swap to `claude-opus-4-8` for deeper coaching |

> The original spec pinned `claude-sonnet-4-20250514`, which is deprecated (retires
> 2026-06-15). `claude-sonnet-4-6` is its official replacement and the right
> cost/latency point for frequent small coaching calls.

### Tests

```sh
cd backend && .venv\Scripts\python -m pytest    # 20 tests, SQLite + faked Claude client
```

---

## How the AI coaching works

There are four AI jobs, each with its own prompt, trigger, and JSON schema
([backend/app/services/prompts.py](backend/app/services/prompts.py)):

| Job                 | Endpoint                          | Regenerates when…                              |
| ------------------- | --------------------------------- | ---------------------------------------------- |
| Next session plan   | `/api/coaching/next-session`      | snapshot > 6h old **or** a new session logged  |
| Plateau detector    | `/api/coaching/plateau/{id}`      | 3+ new sessions of that exercise (needs ≥ 4 total) |
| Weekly review       | `/api/coaching/weekly-review`     | 6h / new session, scoped to the current week   |
| Deload advisor      | `/api/coaching/deload-check`      | 6h / new session (needs ≥ 4 sessions in 3 weeks) |

The non-obvious parts that make it feel like a coach rather than a template generator:

- **Caching, not real-time AI.** Results are cached in `coaching_snapshots` keyed by
  request params, and only regenerate when meaningful new data exists. The GET endpoint
  returns the cached snapshot (or a `stale` envelope with the previous content for
  instant display); the client then calls `POST …/generate`.
- **Streaming.** Generation streams NDJSON (`{"type":"delta"}` lines, then a validated
  `{"type":"result"}`). The UI extracts readable fields (coaching note, headline) from
  the partial JSON so you watch the coach "type", not a spinner.
- **Guaranteed-valid JSON.** Calls use the Claude API's structured outputs
  (`output_config.format` with a JSON schema), so responses always parse — no
  retry-on-bad-JSON machinery.
- **Client-normalized strength data.** Epley estimated 1RMs (`weight × (1 + reps/30)`)
  are computed server-side and fed into every prompt, so the model reasons over a
  normalized baseline instead of raw set data.
- **RPE drives progression.** Set-level RPE detects grinding vs. headroom (≤7 → add
  weight, 8 → hold, 9–10 → reduce volume); session-level RPE catches general fatigue.
  Both are optional everywhere — prompts render "not rated" rather than breaking.
- **Injury notes are first-class.** Whatever you write in your profile is passed
  verbatim into every prompt with an explicit instruction never to violate it.
- **Target-muscle inference.** "What should I do today?" defaults to your three
  least-recently-trained muscle groups; the home screen has Push/Pull/Legs/Upper
  presets to override.

Weekly volume is judged against hardcoded MEV/MRV-style ranges per muscle group
([backend/app/constants.py](backend/app/constants.py)): chest 10–20, back 10–25,
quads 12–20, hamstrings 10–20, shoulders 16–22, biceps 10–14, triceps 10–14, calves 8–16.

## Importing your lift history

Seed the coach with your existing numbers on day one (Profile → *Import lift history*),
or via curl:

```sh
curl -F "file=@history.csv" http://localhost:8000/api/import/csv
```

CSV format — one session is created per distinct date; unknown exercises are created
as custom entries:

```csv
date,exercise,weight_kg,reps,rpe,is_warmup,notes
2026-06-01,Barbell Bench Press,100,8,8,,felt strong
2026-06-01,Barbell Bench Press,100,7,9,,
2026-06-03,Back Squat,140,5,8,,
```

Only `date,exercise,weight_kg,reps` are required.

## API overview

All routes are under `/api` (interactive docs at http://localhost:8000/docs):

- `POST/GET/PATCH/DELETE /sessions`, `POST /sessions/{id}/sets`, `PATCH|DELETE /sets/{id}`
- `GET/POST /exercises`, `GET /exercises/{id}/history` (per-session sets + e1RM trend)
- `GET/PUT /profile` — goal, experience, equipment, injury notes, units (kg/lbs display;
  storage is always kg)
- `GET /stats/weekly-volume` — working sets per muscle vs. recommended ranges
- `GET /coaching/*` + `POST /coaching/*/generate` — see table above; plus
  `GET /coaching/plateau-alerts` for the home-screen badges
- `POST /import/csv`

## Project notes

- **Single-user MVP.** Every request acts as a fixed default user; the schema carries
  `user_id` everywhere so auth can be added later without migrations.
- **Postgres in production shape** (`uuid`, `text[]`, `jsonb` via Alembic migration);
  the same models run on SQLite for dev/tests through cross-dialect type decorators.
  On SQLite the schema is auto-created at startup; on Postgres use `alembic upgrade head`.
- **Active-session state** lives in Zustand persisted to localStorage: refreshes lose
  nothing, and sets that fail to POST (gym dead-zones) are marked *pending* and retried
  on the next log / on finish.
- **Exercise picker works offline** — the library is mirrored to localStorage and
  searched client-side.
