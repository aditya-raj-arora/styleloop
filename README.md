# VogueVault

An AI wardrobe manager. Users upload their clothes; the app auto-tags them, tracks
laundry state, and generates fresh, weather-aware, non-repeating daily outfit
suggestions via a novelty-optimizing rotation engine with swipe feedback. Also
renders outfits on the user's own photo via virtual try-on (the FASHN model,
called through fal.ai).

> **Status:** Sprints 1-4 are implemented — auth, the upload/tagging pipeline,
> the rotation engine (weather-aware, taste-weighted, non-repeating), laundry
> management, and virtual try-on. See [docs/TASKS.md](docs/TASKS.md) for what's
> shipped vs. still planned (Sprint 5: beta hardening & launch).

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
docker compose up -d          # Postgres + Redis (see "Local infra" below)
alembic upgrade head          # create tables
python scripts/seed.py        # optional: demo user + varied garments to develop against
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
docker compose up -d                    # Postgres 16 + Redis 7 + RQ worker
docker compose --profile minio up -d    # ...plus local MinIO for object storage
```

## Deployment

- **Frontend:** Vercel, auto-deploys on push to `main` via its GitHub
  integration.
- **Backend:** a self-managed EC2 box (Caddy for TLS, systemd for the API +
  RQ worker services). `.github/workflows/deploy.yml` SSHes in and deploys
  automatically once CI passes on `main` — see
  [docs/deploy-ec2-setup.md](docs/deploy-ec2-setup.md) for the one-time
  secrets setup it needs.

## Repo layout

```
voguevault/
  backend/      FastAPI app, models, routers, services, RQ worker, tests
  frontend/     React + TS + Vite app
  docs/         TASKS.md and planning docs
  .github/      CI + CD workflows
```

## Branching

- `main` — protected, **including for admins** (`enforce_admins` is on): CI
  must pass on a PR before anything lands, no direct pushes, not even from
  the repo owner. Promote `develop` → `main` by opening a PR and merging it
  (`gh pr create --base main --head develop && gh pr merge --merge`), never
  `git push origin main` directly — that used to silently bypass the rule
  (`enforce_admins` was off); it now just fails. A merge to `main` also
  triggers the EC2 backend deploy — see "Deployment" above.
- `develop` — integration branch for in-progress sprint work. Feature/fix
  branches merge here first (also via PR, CI-gated), then batches of
  `develop` promote to `main` together.
