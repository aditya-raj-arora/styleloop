# Secrets rotation checklist

Every secret VogueVault depends on, where it lives, and how to rotate it
without an outage. Nothing here needs to happen on a schedule yet — this is
the runbook to have ready *before* a rotation is urgent (a suspected leak, an
employee/contributor offboarding, a routine annual rotation), not a task to
run through now.

All secrets currently live in one place: the EC2 box's
`/home/ubuntu/styleloop/backend/.env` (read by both the `styleloop-api` and
`styleloop-worker` systemd services via `EnvironmentFile=`) plus the
equivalent Vercel/GitHub Actions secret stores for the frontend and CI/CD.
There is no automated rotation for any of them.

## General procedure

For any secret below, the safe order is:

1. **Generate the new value** at the provider (or locally, for `JWT_SECRET`)
   — don't revoke the old one yet.
2. **Update it** in every place it's configured (see each entry's "Where
   it's set").
3. **Restart the affected service(s)** so the new value takes effect:
   ```bash
   ssh -i <your .pem> ubuntu@15.252.168.183 "sudo systemctl restart styleloop-api styleloop-worker"
   ```
4. **Verify** — `curl https://15-252-168-183.sslip.io/health` returns
   `{"status":"ok"}`, then exercise the specific feature that secret gates
   (see each entry).
5. **Only then revoke the old value** at the provider, once step 4 confirms
   the new one works.

## Per-secret notes

### `JWT_SECRET`

- **Where it's set:** EC2 `.env` only.
- **Rotation impact:** every existing JWT (every logged-in user's session)
  is invalidated immediately — this is the one rotation that's disruptive by
  design, not just a risk to manage around. Users get logged out and have to
  log back in; there's no way to rotate this one "for free."
- **How to generate:** `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- **Verify:** log in as a test user, confirm a protected endpoint
  (`GET /auth/me`) works with the new token and 401s with an old one.

### `DATABASE_URL` (Neon Postgres)

- **Where it's set:** EC2 `.env`; also whatever pulls it for local dev
  (each contributor's own `.env`, never committed).
- **Rotation:** create a new role/password in the Neon console (or use
  Neon's built-in credential reset), update the connection string, restart.
  Neon supports this without downtime if you create the new role before
  revoking the old one.
- **Verify:** `/health` plus a real DB round-trip (e.g. `GET /garments` as a
  logged-in user).

### `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` (S3)

- **Where it's set:** EC2 `.env`.
- **Rotation:** create a new IAM access key on the same IAM user/role
  *before* deactivating the old one (AWS allows two active keys per user for
  exactly this reason). Update `.env`, restart, verify, then deactivate (not
  delete, initially — deactivate first, delete after a day or two with no
  errors) the old key.
- **Verify:** upload a garment end-to-end (upload → worker processes it →
  `processed_url` populates in the Wardrobe grid).

### `GEMINI_API_KEY`

- **Where it's set:** EC2 `.env`.
- **Rotation:** generate a new key in Google AI Studio, update, restart.
- **Verify:** upload a garment and confirm it gets tagged (category/pattern/
  etc. populate, not just the color extraction that works without this key).

### `OPENWEATHER_API_KEY`

- **Where it's set:** EC2 `.env`.
- **Rotation:** generate a new key at OpenWeatherMap, update, restart. Note
  OpenWeatherMap keys can take up to ~2 hours to activate after creation —
  generate the new one *before* revoking the old one, with margin.
- **Verify:** `GET /outfits/daily` still returns weather-influenced results
  (or at minimum doesn't error — it silently falls back to
  `DEFAULT_LAT`/`DEFAULT_LON` on failure, so check logs/Sentry for a weather
  API error, not just the response).

### `FASHN_API_KEY` (a fal.ai key, not FASHN-issued — see `services/tryon.py`)

- **Where it's set:** EC2 `.env`.
- **Rotation:** generate a new key in the fal.ai dashboard, update, restart.
- **Verify:** request a try-on render end-to-end (needs a base photo already
  uploaded).

### `SENTRY_DSN`

- **Where it's set:** EC2 `.env` (currently unset — see Sprint 5's
  Observability section in [TASKS.md](TASKS.md)).
- **Rotation:** a DSN isn't really a secret in the traditional sense (it's
  meant to be embeddable in client code for browser SDKs), but if the
  project is ever rotated to a new Sentry project, just swap the value and
  restart — no coordination needed, it only affects where new events go.

### EC2 deploy key (`EC2_SSH_KEY` GitHub Actions secret)

- **Where it's set:** GitHub repo secrets
  (`Settings → Secrets and variables → Actions`) and the EC2 box's
  `~/.ssh/authorized_keys`.
- **Rotation:** generate a new keypair, append the new public key to
  `authorized_keys` *before* updating the GitHub secret or removing the old
  public key line — see [docs/deploy-ec2-setup.md](deploy-ec2-setup.md) for
  the exact commands (same process as the initial setup, just swapping
  keys). Remove the old key's line from `authorized_keys` only after
  confirming a deploy succeeds with the new one.
- **Verify:** push a no-op commit to `main` (or re-run the CI workflow) and
  watch the **Deploy backend (EC2)** run succeed in the Actions tab.

### `EC2_HOST` / `EC2_USER`

Not secrets in the sensitive sense, but stored as GitHub secrets alongside
the key for convenience. Update them the same way if the box's IP changes or
a different deploy user is used — no coordination needed, they take effect
on the next deploy.
