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

## Sprint 4 — Virtual try-on

**Correction to the Sprint 1 stub:** `services/tryon.render_tryon` and
`workers/tasks.generate_tryon` currently take a single `garment_id` — but
try-on renders an *outfit* (top+bottom, or a dress, plus whatever else the
rotation engine picked), not one garment in isolation. Both need to take
`outfit_id` (→ `Outfit.garment_ids`) instead. Caught while planning this
sprint, not yet fixed in code.

### Base photo

- [ ] `User.base_photo_version: int` (new column, default 0) — `base_photo_url`
      alone can't tell "the user re-uploaded the same slot" from "still the
      old photo," and the try-on cache key needs that distinction.
- [ ] `POST /users/me/photo` (multipart, same size/type validation as
      `POST /garments`): upload to the bucket, set `base_photo_url` to the new
      key, bump `base_photo_version`. Bumping the version is what
      invalidates old cached renders — they're keyed by version, not deleted.
- [ ] Frontend: a base-photo upload control. Leaning toward putting it
      directly on the Dashboard (prompt when `base_photo_url` is null,
      "Update photo" once set) rather than a whole new `/profile` route —
      it's the only thing that would live there. Revisit if that gets
      cramped once try-on's own UI is in place.

### Try-on generation

- [ ] `tryon_renders` table: `id`, `user_id`, `outfit_id` (FK), `photo_version`,
      `rendered_url` (storage key), `created_at`. The cache key is
      `(user_id, outfit_id, photo_version)` — look up a matching row before
      generating anything new.
- [ ] `services/tryon.render_tryon(user_id, outfit_id, photo_version)`: calls
      FASHN via fal.ai. **Open question to resolve during implementation**:
      FASHN's API renders one garment onto a photo at a time — an outfit with
      outerwear/shoes may need multiple layered calls, or a v1 that only
      renders the "anchor" garment (the top, or the dress) and accepts that
      as a known limitation. Decide once actually looking at FASHN's API
      docs, not guessed here.
- [ ] `workers/tasks.generate_tryon(user_id, outfit_id)`: idempotent like
      `process_garment` — look up the outfit + user's current
      `base_photo_url`/`base_photo_version`, render, upload the result,
      insert the `tryon_renders` row. Never crashes the worker on a FASHN
      error — logs and leaves the row absent so the API's fallback path
      (below) kicks in.
- [ ] `TRYON_DAILY_CAP` setting (config.py) — a plain per-user count of
      `tryon_renders` rows created today; reject new generation over the cap
      (cached hits don't count against it — they cost nothing to re-serve).

### API

- [ ] `POST /outfits/{id}/tryon`: cache hit → return the cached render
      immediately. Cache miss → over the daily cap → 429 with a clear detail
      message. Otherwise enqueue `generate_tryon` and return 202 (same
      immediate-202-then-poll shape as `POST /garments`).
- [ ] `GET /outfits/{id}/tryon`: poll endpoint — null/pending until the
      worker's row lands, matching the `processed_url` polling pattern
      Wardrobe already uses.

### Frontend

- [ ] Dashboard: a "Try it on" button on the daily outfit card, on-demand
      only (never auto-triggered — it costs real money per render). Polls
      like Wardrobe's garment grid does. On cap/error, falls back to the
      existing flat outfit view rather than showing a broken state — that
      view already exists and needs no changes for this.

### Testing

- `services/tryon` and the worker task: mock the FASHN/fal.ai call
  (monkeypatch, same pattern as `test_tagging.py`/`test_bg_removal.py`) —
  cache-hit short-circuits generation, daily cap is enforced, a
  provider error doesn't crash the task.
- `/outfits/{id}/tryon` endpoint: cache hit returns immediately, cap
  rejection is a clean 4xx, ownership checks (404 for another user's
  outfit) match the existing `/outfits` tests.

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
