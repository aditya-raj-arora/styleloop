# StyleLoop

An AI wardrobe manager. Users upload their clothes; the app auto-tags them, tracks
laundry state, and generates fresh, weather-aware, non-repeating daily outfit
suggestions via a novelty-optimizing rotation engine with swipe feedback. A later
release adds virtual try-on (rendering outfits on the user's photo via the FASHN API
through fal.ai).

> **Sprint-1 status:** This is scaffolding only — real models, a running API skeleton,
> a typed frontend shell, and CI/CD. Business logic is stubbed with clear TODOs. The ML
> and auth logic are intentionally **not** implemented yet.

## Architecture

```
frontend (React + TS + Vite)  ──HTTP──▶  backend (FastAPI)
                                             │
                              ┌──────────────┼───────────────┐
                              ▼              ▼               ▼
                        PostgreSQL        Redis + RQ      external APIs
                        (SQLAlchemy)      (async jobs)    (OpenWeather, FASHN/fal.ai)
```

- **Backend:** FastAPI, SQLAlchemy 2.0 (typed `mapped_column`), Alembic, pydantic-settings,
  PostgreSQL, Redis + RQ for async jobs.
- **Frontend:** React 18 + TypeScript + Vite, React Router, TanStack Query, Zustand.
- **Infra:** docker-compose (Postgres + Redis), GitHub Actions CI + CD, Dockerfile for backend.

## Key contracts

- **Garment API shape** is defined by [`backend/app/schemas/garment.py`](backend/app/schemas/garment.py)
  (`GarmentOut`). This is the **frozen contract** between frontend and backend; both build
  against it in parallel.
- **Auth** uses a JWT passed in the `Authorization: Bearer <token>` header.
- **Uploads return immediately.** The worker processes bg-removal + tagging asynchronously;
  the frontend shows a placeholder until `processed_url` is populated.

## Guardrails

- **Secrets only in `.env`.** `.env` is git-ignored from the first commit; keep
  `.env.example` current. Never commit real secrets.
- **Storage buckets are private**, signed URLs only. **Never log user photos** or put them
  in URLs.
- **Slow work always goes through the RQ worker**, never blocks a request.
- **Try-on is on-demand + cached + per-user daily cap**, with graceful fallback to the flat
  (non-rendered) outfit view.

## Getting started (backend)

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# POSIX:    source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env          # then fill in real values
ruff check .
pytest -q
uvicorn app.main:app --reload
```

## Getting started (frontend)

```bash
cd frontend
npm install
cp .env.example .env
npm run dev                   # http://localhost:5173
```

## Local infra

```bash
docker compose up -d          # Postgres 16 + Redis 7
```

## Repo layout

```
styleloop/
  backend/      FastAPI app, models, routers (stubbed), services (stubbed), worker, tests
  frontend/     React + TS + Vite shell (pages/components stubbed)
  docs/         TASKS.md and planning docs
  .github/      CI + CD workflows
```

## Branching

- `main` — protected; CI must pass before merge.
- `develop` — integration branch for Sprint-1 work.
