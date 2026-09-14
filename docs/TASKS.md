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

- [x] **`weather.get_weather`** (OpenWeatherMap lat/lon → `{temp_c, condition, rain}`)
      with a short-TTL cache. Needed by the engine next sprint.
- [x] **Scoring spike**: pure function `score_outfit(...)` implementing
      `validity + recency_penalty + fairness + taste_weight`, with **unit tests over
      synthetic garments** (no DB). Validate the per-day `(user_id, date)` seed →
      deterministic-but-varying behavior. Write it up as a short design note.
      (Added a 5th term, `day_jitter`, to actually make the per-day seed
      produce varying-but-reproducible rankings — see
      docs/rotation-scoring-design-note.md.)
- [x] **Seed script** `scripts/seed.py`: demo user + N varied garments for local dev
      (helps A and B test without hand-uploading).
- [x] **Test harness**: pytest fixtures for an ephemeral test DB + factory helpers;
      wire into CI so DB-touching tests run.
- [x] **Frontend**: Dashboard + Swipe skeletons rendering **mock** outfit data
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

## Sprint 2 — Rotation engine + Daily outfit *(the differentiator)* ✅

- [x] Implement `rotation.generate_outfits`/`generate_candidates`: score
      candidates (top+bottom, or a dress; + outerwear when cold; + shoes when
      available) over **clean-only, tagged** garments via `score_outfit`;
      return the best non-overlapping combinations. See
      docs/rotation-scoring-design-note.md for the algorithm.
- [x] `GET /outfits/daily` (generate-and-persist on first request per day,
      idempotent afterwards) + `POST /outfits/generate` ("regenerate" —
      prefers a combination distinct from today's current one).
- [x] `POST /outfits/{id}/feedback` → records a `FeedbackEvent`
      (like/dislike/skip).
- [x] `POST /outfits/{id}/wear` → mark each garment worn (state, `wear_count`,
      `last_worn_at`).
- [x] Dashboard: today's outfit, "regenerate", "wore this" (real data,
      replacing the Sprint 1 mock).
- [x] Swipe: swipes the real daily outfit — skip records "dislike" and
      regenerates, like records "like".
- **Not wired yet:** a weather chip in the UI (weather is used server-side to
  filter outerwear/validity, but isn't surfaced to the user); `taste_weight`
  stays unpopulated until Sprint 3 aggregates real `FeedbackEvent` data;
  location comes from browser geolocation (falls back to a fixed default city
  when denied/unavailable) rather than a saved per-user location.
- **Milestone:** weather-aware, non-repeating daily suggestion you can accept. ✅

## Sprint 3 — Feedback loop + laundry UX + polish

`POST /outfits/{id}/feedback` already records a `FeedbackEvent` (Sprint 2) —
nothing reads that history back into scoring yet. That's this sprint's core.

### Taste weighting ✅

- [x] `services/taste.py`: `compute_taste_weights(db, user_id) -> dict[str, float]`
      — aggregates `FeedbackEvent` per garment category. `like: +1`,
      `dislike: -1`, `skip` ignored. Recent events outweigh stale ones via
      exponential decay (14-day half-life), not a flat sum, so one bad week
      doesn't permanently poison a category.
- [x] Wired into `routers/outfits.py::_generate_and_persist` — daily
      generation now uses real learned preference instead of
      `taste_weights=None`.
- [x] Tests (`test_taste.py`): empty-feedback → empty weights, like/dislike
      sign, skip ignored, recent feedback outweighing old, untagged garments
      contributing nothing.

### Rotation feels fair — close the "regenerate" gap ✅

- [x] `exclude_combo` → `exclude_combos`: regenerate now excludes every exact
      outfit generated for the user in the last 7 days (`_LOOKBACK_DAYS` in
      `routers/outfits.py`), not just today's — still degrades gracefully
      (returns the best available) when there's truly no alternative.
- [ ] Revisit `fairness`/`recency_penalty` weighting now that real wear data
      exists instead of the seed script's synthetic spread — deferred, needs
      real usage data to tune against rather than guessing.

### Laundry UX ✅

- [x] Bulk "Do Laundry" endpoint: `POST /garments/laundry/reset` flips every
      `laundry`-state garment for the user back to `clean` in one call.
- [x] Wardrobe UI: filter chips (All/Clean/Worn/Laundry) + a "Do Laundry (N)"
      bulk button that appears whenever there's something to reset;
      `GarmentCard` gained a state badge and a "To laundry" quick action.
- [x] Worn→laundry transition: **user-initiated only** — `wear` still just
      bumps `wear_count`/`last_worn_at`; nothing moves a garment into
      `laundry` automatically. Revisit an automatic-after-N-wears trigger
      once real usage shows a sensible N.

### Polish pass ✅

- [x] Empty/loading/error states audited across Dashboard/Swipe/Wardrobe/
      Upload — all four already had reasonable coverage from Sprint 1/2/3;
      added `aria-live`/`role="alert"` so status changes and errors are
      actually announced, not just visible.
- [x] **Fixed a real navigation bug found during this pass**: `/swipe` had a
      route (`App.tsx`) but no `Navbar` link — unreachable except by typing
      the URL directly. Navbar now links to all four routes.
- [x] **Fixed a real contrast bug found during this pass**: `WardrobeBackground`
      goes dark at night (matching `AnimatedBackground`'s day/night theming)
      but `Wardrobe.tsx`'s text was hardcoded for its pale daytime gradient
      only — nearly unreadable after dark. New `useIsNight` hook (shared,
      same cutoff `AnimatedBackground`/`WardrobeBackground` already used) lets
      the page's text/chip colors follow its background's mode.
- [x] **Fixed a real mobile bug found during this pass**: no `color-scheme`
      meta anywhere, so a mobile browser that auto-inverts unstyled
      light-only pages for a device dark preference (e.g. Android Chrome's
      "Auto Dark Theme for Web Contents") rendered default-colored text
      unreadable against a forced-dark background — reproduced in a mobile
      viewport, confirmed the fix (`<meta name="color-scheme" content="light">`
      + an explicit `background: white` on `html, body`) resolves it.
- [x] Mobile layout pass: responsive text sizing (Dashboard/Wardrobe/Upload
      headings), Wardrobe's garment grid now scales 2→3→4 columns instead of
      always 2, Swipe's `pb-24` fix (content was tucked behind the fixed
      Navbar on short viewports — missed in the Sprint 2 PR), smaller
      dropzone padding on Upload. Verified visually in a 375×812 mobile
      viewport (Login, Dashboard, Wardrobe, Swipe, Upload).
- [x] Basic accessibility: `aria-label`s on every icon-only Navbar link/button
      (previously unlabeled), `aria-pressed` on Wardrobe's filter toggles,
      `aria-current="page"` for the active nav route, visible
      `focus-visible` outlines on every custom button/link (previously relied
      on browser default, inconsistent across the dark nav bar and colored
      buttons), Swipe's Skip/Like buttons gained explicit `text-white` (they
      had none — default text color on a red/green background was a genuine
      contrast failure, not just unstyled-focus).

- **Milestone:** the engine visibly learns taste and rotation feels fair. ✅

Sprint 3 is now fully done.

## Sprint 4 — Virtual try-on ✅

**Correction to the Sprint 1 stub, fixed:** `services/tryon.render_tryon`
and `workers/tasks.generate_tryon` now take `outfit_id` (→
`Outfit.garment_ids`), not a single `garment_id`.

**Resolved open question:** checked FASHN's actual API
([fal.ai/models/fal-ai/fashn/tryon/v1.6](https://fal.ai/models/fal-ai/fashn/tryon/v1.6/api)) —
it takes exactly one `garment_image` per call (`category`:
`tops`/`bottoms`/`one-pieces`/`auto`, no outerwear/shoes) and cannot
composite multiple garments. Went with **sequential chaining**: render the
first garment onto the base photo, then render the second onto *that*
output, and so on. Outerwear/shoes are silently skipped (no matching FASHN
category) rather than failing the whole render — a coat still shows the
shirt+pants underneath.

### Base photo ✅

- [x] `User.base_photo_version: int` (new column, default 0).
- [x] `POST /auth/me/photo` (multipart, same size/type validation as
      `POST /garments`) — uploads, sets `base_photo_url`, bumps
      `base_photo_version`. (Landed on `/auth/me/photo`, next to the existing
      `/auth/me`, rather than a separate `/users` router.)
- [x] Frontend: base-photo prompt/upload control on the Dashboard, as
      planned (no separate `/profile` route).

### Try-on generation ✅

- [x] `tryon_renders` table — `(user_id, outfit_id, photo_version)` unique
      constraint doubles as the cache key.
- [x] `services/tryon.render_tryon(base_photo_url, garments)`: sequential
      FASHN-through-fal.ai calls (queue submit → poll status → fetch
      result), per the resolved design above. Pure-ish — takes URLs/a
      garment list, no DB access; the worker owns persistence.
- [x] `workers/tasks.generate_tryon(user_id, outfit_id)`: idempotent (a
      cache hit short-circuits before spending a FASHN call), never raises
      on a render failure — logs and leaves no row, so the API's fallback
      path (below) applies.
- [x] `TRYON_DAILY_CAP` setting (default 5) — counts `tryon_renders` rows
      created today; cache hits don't count against it.

### API ✅

- [x] `POST /outfits/{id}/tryon`: cache hit → 202 with the ready render.
      Cache miss + over cap → 429. Otherwise enqueues and returns 202
      pending.
- [x] `GET /outfits/{id}/tryon`: poll endpoint, pending until the worker's
      row lands.

### Frontend ✅

- [x] Dashboard: "Try it on" button (only shown once a base photo exists),
      new `useTryon` hook polls for up to ~30s and then shows a "try again"
      fallback rather than declaring the outfit unrenderable — the worker
      may still finish after the frontend gives up, and the next click hits
      the cache instantly if so.

### Testing ✅

- `test_tryon.py`: `render_tryon` sequencing/chaining, category mapping,
  skip-unsupported-categories, HTTP error wrapping, unexpected-status and
  timeout handling — all FASHN calls mocked.
- `test_workers_tryon.py`: `generate_tryon`'s idempotency (cache hit
  short-circuits), render-order (dress/top/bottom), and failure handling
  (no crash, no row) — run directly against the transactional DB fixtures.
- `test_outfits.py` / `test_auth.py`: cache hit vs. miss, photo-version
  mismatch is treated as a miss, daily cap enforcement (and that it only
  counts *today's* renders), 404 ownership checks, base-photo upload
  version bumping and content-type validation.
- Full suite (108 tests) passes against the real Neon DB, including a live
  `alembic upgrade head` run. `ruff check` clean, `npm run build` clean.

- **Milestone:** outfits rendered on the user's photo, cost-capped and cached. ✅

## Sprint 5 — Beta hardening & launch

Grounded in the actual stack, not a generic checklist: backend is
self-managed on a single EC2 box (Ubuntu, Caddy for TLS via an `sslip.io`
wildcard — no real domain yet), frontend is Vercel (auto-deploys on push to
`main`), DB is Neon Postgres, object storage is S3, CI is GitHub
Actions (`ruff` + `pytest` + a Postgres service container, `npm run build`
— no E2E, no deploy step). "Harden" means closing the gaps that are actually
open, not standing up a first deploy — the app has been live since Sprint 1.

### Deploy automation ✅ candidate for first

- [ ] **The EC2 backend has no CD** — every backend-touching PR this project
      has shipped ended with a manual `ssh` + `git pull` + `alembic upgrade
      head` + `systemctl restart`. Automate it: a GitHub Actions job
      (triggered on push to `main`, after the existing CI passes) that SSHs
      in via a deploy key and runs those same steps. Removes the recurring
      manual step, and makes "pushed to main" actually mean "live" the way
      Vercel's frontend deploy already does.
- [ ] Fix the standing branch-protection bypass: `main` requires PRs, but
      every merge-to-main in this project has gone through a direct
      `git push` (fast-forward from `develop`) that GitHub reports as
      "Bypassed rule violations." Either stop pushing to `main` directly
      (open a PR from `develop` instead) or accept the bypass deliberately
      — but a rule silently bypassed on every single use isn't really a
      rule. Decide and document which.

### Observability

- [ ] Error tracking (Sentry or similar) — wired into both the FastAPI app
      (`main.py`) and the RQ worker (`workers/run.py`); currently a failure
      in either is invisible unless someone happens to be tailing
      `journalctl` on the EC2 box.
- [ ] Structured logging: the worker already logs task failures
      (`generate_tryon`, `process_garment`) via the stdlib `logging` module
      with no configured level/format — set one explicitly (level from an
      env var, not hardcoded) rather than relying on defaults. Re-confirm
      the existing "never log photo bytes/URLs" rule (services/storage.py's
      docstrings already state it) holds through whatever formatter/handler
      gets added.

### Rate limiting + secrets

- [ ] `/auth/signup` and `/auth/login` have no rate limiting — a real gap
      before real users (credential stuffing / signup spam). Add per-IP
      limiting (e.g. `slowapi`) to both.
- [ ] Secrets rotation checklist: `JWT_SECRET`, `STORAGE_*` keys,
      `DATABASE_URL`, `GEMINI_API_KEY`, `OPENWEATHER_API_KEY`,
      `FASHN_API_KEY` all live in one `.env` on the EC2 box with no
      documented rotation process. Write the checklist (what to rotate, in
      what order, how to verify nothing broke) — don't need to execute a
      rotation this sprint, just have the runbook ready before it's urgent.

### E2E tests + CI

- [ ] Playwright suite for the core flows: signup → login → upload →
      wardrobe; generate → regenerate → wear; swipe like/dislike; laundry
      bulk-reset; base-photo upload → try-on (mock FASHN in the test
      environment — a real call costs money and is slow).
- [ ] New CI job running that suite against the full stack (Postgres +
      Redis + backend + frontend, likely via `docker compose` in CI) —
      currently backend and frontend are tested in isolation from each
      other; nothing exercises them together.

### Production polish

- [ ] Real custom domain (replacing the `sslip.io` wildcard for the backend
      and the `*.vercel.app` default for the frontend) — needed for a
      credible beta, not just cosmetic.
- [ ] Onboarding: a fresh signup lands on a Dashboard that 422s
      ("Not enough tagged, clean garments") until the user has uploaded and
      tagged a few things. A first-run checklist (upload N garments → set a
      base photo → see your first outfit) would close that gap instead of
      handing a new user an error.
- [ ] Performance pass — deliberately last, and deliberately vague here:
      revisit once real usage data exists (query patterns, bundle size,
      candidate-generation cost at real wardrobe sizes) rather than
      optimizing against guesses. Current bundle is ~76KB gzipped; not a
      concern yet.

- **Milestone:** shipped to first real users.

---

## Backlog / later (not yet scheduled)

- Calendar/occasion-aware suggestions ("interview tomorrow").
- Shareable outfit links; social/lookbook.
- Wardrobe analytics (cost-per-wear, most/least worn, gaps).
- Packing-list generator for trips (weather + duration aware).
- Multi-photo garments; auto-detect duplicates.
