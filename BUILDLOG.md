## 2026-09-11 — M0: foundation

### Where AI helped
- Generated the full compose.yaml with healthcheck-gated depends_on — caught
  the classic Postgres-not-ready-yet race condition before it happened, not
  after debugging a crash loop
- Wrote the migration runner with a schema_migrations tracking table, so
  re-running migrations is idempotent instead of crashing on "already exists"
- Converted per-1M-token dollar pricing to microdollar integers correctly on
  the first pass (no rounding, no float creep)

### Where AI was wrong
- Initial Supabase Auth verification used a shared HS256 secret
  (SUPABASE_JWT_SECRET) — this is the legacy Supabase signing model. New
  Supabase projects (since May 2025) default to asymmetric ES256 signing,
  verified via a JWKS public-key endpoint, not a shared secret. Discovered
  only when the actual token's header showed alg: ES256 and decode failed
  with "alg value is not allowed." Fixed by switching to PyJWKClient,
  fetching Supabase's public keys instead of relying on a secret my app
  should never have needed to hold in the first place.

### What I changed and why
- Local git branch defaulted to `master`, not `main` — renamed before first
  push so the repo matches the convention used everywhere else in the project
- Ran `docker compose up --build` in the foreground first, which meant the
  whole stack died the moment that terminal closed — switched to `-d`
  (detached) for anything meant to stay running across a session
- Added a UNIQUE constraint on plans.name in a new migration (0002) rather
  than editing 0001 after it had already been applied — migrations stay
  append-only even when I'm the only one who's run them
- Supabase rejected a fabricated email domain (nexusbill.dev) as
  undeliverable, then hit its own send-rate limit before "Confirm email"
  was disabled — switched to a real domain via Gmail plus-addressing and
  turned off email confirmation for this dev-only auth project