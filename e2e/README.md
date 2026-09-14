# E2E tests (Playwright)

Real browser tests against the full stack — frontend + backend + Postgres +
Redis — covering the core flows: signup/login, upload → wardrobe, daily
outfit generate/regenerate/wear, swipe like/dislike, laundry bulk-reset,
base-photo upload → try-on.

## Scope — what this does and doesn't cover

This environment has no `GEMINI_API_KEY`, `DEEPAI_API_KEY`, `rembg`, or
`FASHN_API_KEY` configured (all cost money / need a live account, and
aren't worth spending on every CI run). Two consequences, both intentional
and covered by the backend's own tests instead of here:

- **`upload-wardrobe.spec.ts`** verifies a freshly-uploaded garment appears
  with its "Processing…" placeholder — it does *not* wait for tagging to
  finish, because it never will in this environment. The bg-removal/tagging
  pipeline's own correctness is `test_bg_removal.py`/`test_tagging.py`'s job.
- **`tryon.spec.ts`** verifies a try-on request goes to "pending" — it does
  not wait for a render, which would fail here by design (no FASHN key).
  That's the real "graceful fallback" path the feature was built with (see
  `docs/rotation-scoring-design-note.md`'s Sprint 4 section), exercised for
  real rather than mocked.

Everything else (`auth`, `outfit-flow`, `swipe`, `laundry`) logs in as
`scripts/seed.py`'s demo user (`demo@styleloop.dev`), which is pre-seeded
with already-tagged, `clean` garments — bypassing the async pipeline
entirely so the rotation engine has something real to work with.

## Running locally

Needs Postgres + Redis + MinIO (local S3-compatible storage —
`scripts/seed.py` and any upload need somewhere to put bytes; the plain
`docker compose up -d` in the main README's "Local infra" section skips
MinIO by default, so use the `--profile minio` form here), the backend
migrated and running, the frontend dev server running, and the demo user
seeded:

```bash
# from repo root
docker compose --profile minio up -d

cd backend
python -m venv .venv && source .venv/Scripts/activate  # or .venv/bin/activate on POSIX
pip install -r requirements.txt -r requirements-dev.txt
export STORAGE_ENDPOINT_URL=http://localhost:9000
export STORAGE_ACCESS_KEY=styleloop
export STORAGE_SECRET_KEY=styleloop123
export STORAGE_BUCKET=styleloop-media
# Create the bucket once (MinIO doesn't auto-create it) - e.g. via the
# console at http://localhost:9001 (styleloop / styleloop123), or:
python -c "
import boto3
from botocore.client import Config
boto3.client('s3', endpoint_url='http://localhost:9000', aws_access_key_id='styleloop', aws_secret_access_key='styleloop123', region_name='us-east-1', config=Config(signature_version='s3v4', s3={'addressing_style': 'path'})).create_bucket(Bucket='styleloop-media')
"
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --port 8000 &

cd ../frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev &

cd ../e2e
npm install
npx playwright install --with-deps chromium
npm test
```

## Running in CI

`.github/workflows/e2e.yml` does the above as explicit steps (Postgres/Redis
as service containers, MinIO via a plain `docker run` from `quay.io` — see
that file's comments for why not Docker Hub, and why not a `services:`
entry — backend + frontend started in the background, `scripts/seed.py` run
once) — see that file for the exact sequence. Runs on every push/PR to
`main`/`develop` alongside the existing backend/frontend CI jobs, as its own
job.
