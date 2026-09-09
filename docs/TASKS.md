# VogueVault — Sprints & Task Breakdown

> **Sprint numbering:** the scaffold already on `main` (models, API skeleton,
> frontend shell, green CI/CD) is **Sprint 0 — Foundation (✅ done)**. Everything
> below is forward-looking. Sprints are ~2 weeks; roughly ~10–12 weeks to beta.

## Team & ownership model

Three people, each owning a **full vertical slice** (backend + their frontend
pages), all building against the frozen `GarmentOut` contract in parallel.

| Dev | Role (owner tag in code) | Owns |
| --- | --- | --- |
| **A** | `Backend/Infra` | Auth, DB/migrations, object storage, worker/infra plumbing, CI/CD, deploy. Frontend: Login/auth + protected routes. |
| **B** | `Backend + ML` | Garment upload pipeline, bg-removal, tagging. Frontend: Upload + Wardrobe. |
| **C** | `ML/Engine` | Rotation engine (the differentiator), outfits, weather, feedback. Frontend: Dashboard + Swipe. |

---

## Roadmap at a glance

| Sprint | Theme | Milestone ("I can…") |
| --- | --- | --- |
| **0** ✅ | Foundation / scaffold | "Repo builds, CI is green, contracts are frozen." |
| **1** | Auth + Wardrobe pipeline | "Sign up, upload a photo, watch it auto-tag, browse my wardrobe." |
| **2** | Rotation engine + Daily outfit **(differentiator)** | "It tells me what to wear today — weather-aware, non-repeating." |
| **3** | Feedback loop + laundry UX + polish | "It learns my taste, and the rotation feels fair." |
| **4** | Virtual try-on | "See the outfit rendered on me." |
| **5** | Beta hardening & launch | "Ship to first real users." |

---

## Sprint 1 — Auth + Wardrobe pipeline

**Goal:** an authenticated user uploads a garment; the RQ worker does bg-removal +
tagging async; the wardrobe grid shows a placeholder that resolves into the tagged
cutout. This proves the auth story, the async pipeline, and the frozen contract
end-to-end.

**Not in scope this sprint:** outfit generation, weather, swipe, try-on.

### Dev A — `Backend/Infra` (Auth + platform)

- [x] **Initial Alembic migration** for all 4 tables; wire `alembic upgrade head`
      into local bootstrap + CI (spin up a Postgres service in `ci.yml` backend job).
- [x] **Password hashing** (argon2 or bcrypt via `passlib`) + **JWT** issue/verify
      helpers reading `JWT_SECRET`/`JWT_ALGORITHM`/`JWT_EXPIRE_MINUTES`.
- [x] Implement **`POST /auth/signup`** and **`POST /auth/login`** → return a JWT.
- [x] **`get_current_user`** FastAPI dependency: decode `Authorization: Bearer`,
      load the `User`, 401 on failure. Export for B and C to reuse.
- [x] **Object storage adapter**: private bucket + presigned upload/download URLs
      (S3 / Cloudflare R2 / local MinIO for dev). Never logs bytes or puts photos in URLs.
- [x] **docker-compose**: add a `worker` service (`rq worker`) and optional `minio`.
- [x] **Frontend**: Login/Signup form → auth endpoints; store JWT in `useAuth`
      (in-memory); `RequireAuth` wrapper redirecting unauthenticated users to `/`.
- **Acceptance:** sign up → log in → call a protected endpoint with the Bearer
  token and get 200; migrations run clean in CI.

### Dev B — `Backend + ML` (Upload + tagging)

- [x] **`POST /garments`** (multipart): store raw to the bucket (A's adapter),
      create `Garment` (`state='clean'`), enqueue `process_garment(id)`, return
      `GarmentOut` **202 immediately** (`processed_url` null).
- [x] **`GET /garments`** (user-scoped list) + **`GET /garments/{id}`** (404 if not owned).
- [x] **`bg_removal.remove_background`**: rembg (U2Net) local, remove.bg fallback.
- [x] **`tagging.tag_garment`**: deterministic color (k-means in LAB → named palette);
      category/pattern/season/formality via a Claude vision zero-shot call; fabric
      confidence → `None` below threshold. (Team called an audible on CLIP vs.
      vision-LLM — see the PR description for why.)
- [x] **Worker `process_garment`**: bg-removal → tagging → upload processed →
      set `processed_url` + tags → commit. Idempotent + safe to retry.
- [x] **`PATCH /garments/{id}/tags`** (`TagUpdate`) and **`POST /garments/{id}/state`**
      (clean/worn/laundry; on "worn" bump `wear_count` + `last_worn_at`).
- [x] **Frontend**: Upload page (file picker + optimistic placeholder card) and
      Wardrobe grid (`GarmentCard`, refetch/poll until `processed_url` populated).
- **Acceptance:** upload a photo → card shows "Processing…" → resolves to cutout +
  tags within a few seconds; wardrobe lists all of the user's garments.

### Dev C — `ML/Engine` (Rotation groundwork + test infra)

Rotation lands in Sprint 2; Sprint 1 de-risks it and unblocks everyone.

- [ ] **`weather.get_weather`** (OpenWeatherMap lat/lon → `{temp_c, condition, rain}`)
      with a short-TTL cache. Needed by the engine next sprint.
- [ ] **Scoring spike**: pure function `score_outfit(...)` implementing
      `validity + recency_penalty + fairness + taste_weight`, with **unit tests over
      synthetic garments** (no DB). Validate the per-day `(user_id, date)` seed →
      deterministic-but-varying behavior. Write it up as a short design note.
- [ ] **Seed script** `scripts/seed.py`: demo user + N varied garments for local dev
      (helps A and B test without hand-uploading).
- [ ] **Test harness**: pytest fixtures for an ephemeral test DB + factory helpers;
      wire into CI so DB-touching tests run.
- [ ] **Frontend**: Dashboard + Swipe skeletons rendering **mock** outfit data
      against the contract, so the UI is ready when the engine ships.
- **Acceptance:** `pytest` covers the scoring function + determinism; weather returns
  the normalized dict; `seed.py` populates a demo wardrobe.

### Definition of Done (every task)

Code + tests + **green CI** + reviewed PR merged into `develop`. Demoable at sprint review.

### Contract-change protocol

`GarmentOut` is frozen. Any change is **one PR** touching both
`backend/app/schemas/garment.py` and `frontend/src/api/client.ts`, reviewed by the
other affected owner. No silent drift.

---

## Sprint 2 — Rotation engine + Daily outfit *(the differentiator)*

- Implement `rotation.generate_outfits`: score candidates over **clean-only**
  garments; weather-aware filtering (season/formality vs. today's weather);
  per-day seed for stable-but-fresh suggestions; novelty optimization.
- `GET /outfits/daily` (generate on first request) + `POST /outfits/generate`.
- `POST /outfits/{id}/wear` → mark each garment worn (state, `wear_count`, `last_worn_at`).
- Dashboard: today's outfit, weather chip, "regenerate", "wore this".
- **Milestone:** weather-aware, non-repeating daily suggestion you can accept.

## Sprint 3 — Feedback loop + laundry UX + polish

- `POST /outfits/{id}/feedback` → `FeedbackEvent`; feed `taste_weight` into scoring.
- Laundry management UI: clean ↔ worn ↔ laundry; "do laundry" resets state in bulk.
- Tune fairness/novelty so the whole wardrobe rotates; guard against degenerate repeats.
- Empty/loading/error states, mobile layout, accessibility pass.
- **Milestone:** the engine visibly learns taste and rotation feels fair.

## Sprint 4 — Virtual try-on

- Base-photo upload (versioned) to the private bucket.
- `tryon.render_tryon` via **FASHN through fal.ai** in the worker; **cache by
  `(photo_version, garment_id)`**; **per-user daily cap**; graceful fallback to the
  flat outfit on cap/error.
- Try-on view in the Dashboard, on-demand only.
- **Milestone:** outfits rendered on the user's photo, cost-capped and cached.

## Sprint 5 — Beta hardening & launch

- Structured logging/observability (never log photos), error tracking (e.g. Sentry).
- Rate limiting + basic abuse protection; secrets rotation checklist.
- E2E tests (Playwright) for the core flows; expand CI.
- Production deploy + custom domain; onboarding flow; performance pass.
- **Milestone:** shipped to first real users.

---

## Backlog / later (not yet scheduled)

- Calendar/occasion-aware suggestions ("interview tomorrow").
- Shareable outfit links; social/lookbook.
- Wardrobe analytics (cost-per-wear, most/least worn, gaps).
- Packing-list generator for trips (weather + duration aware).
- Multi-photo garments; auto-detect duplicates.
