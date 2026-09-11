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

## 2026-09-11 — M1: Organization, Project, API Key management

### Where AI helped
- Extracted `get_caller_org` / `get_owned_project` as shared FastAPI
  dependencies early, once the same org-scoping lookup was needed a second
  time — meant tenant isolation is enforced structurally (no ID parameter
  to manipulate, no per-route check to forget) rather than reimplemented,
  and easy to get subtly wrong, in every route
- Caught that a hard-delete on projects would either FK-violate or silently
  orphan billing history — archived_at was already in the schema for this
  exact reason, so "soft delete" wasn't a new decision, just correctly
  implementing what M0's schema had already committed to
- Designed key storage as hash-only from the start (SHA-256, not bcrypt —
  the key's 256 bits of randomness makes slow hashing pointless, unlike a
  human-chosen password), with `response_model` structurally preventing the
  full key from ever being returned after creation, not just relying on
  route code to remember not to

### Where AI was wrong
- Gave SQLModel `Organization`/`Plan` classes without registering `Plan` in
  a shared `models/__init__.py` import path — SQLAlchemy's ORM needs every
  FK-referenced table mapped to a loaded Python class to resolve insert
  order, not just present in the actual database. First register() attempt
  failed with NoReferencedTableError as a result
- `app/db.py`'s `create_engine()` needed an explicit `+psycopg` driver
  suffix — SQLAlchemy defaults a bare postgresql:// URL to psycopg2, which
  isn't installed (project deliberately uses psycopg3). Silent, confusing
  failure mode: the container process stayed "Up" while unable to serve
  any request, because only the reload-supervised worker subprocess
  crashed on import — made a driver mismatch look like a network hang
- Wrote the original register() with no rollback path for a Supabase-
  signup-succeeds-then-local-DB-fails scenario, leaving an orphaned
  Supabase user with no org. Fixed by adding a compensating delete call —
  then that same compensating call crashed too (SUPABASE_SERVICE_ROLE_KEY
  unset from a not-yet-recreated container), which silently masked the
  *original* error. Second fix: rollback failures must never hide the
  primary failure — surface both, always
- Gave a `migrations/0003_organizations_owner.sql` file's contents in chat
  but it was never actually saved to disk — three separate bugs got
  chased and fixed downstream before the real cause (a missing column)
  surfaced. Worth double-checking file creation, not just giving content

### What I changed and why
- Added `pydantic[email]` (EmailStr needs email-validator, not bundled by
  default) and swallowed one more rebuild-vs-restart distinction: new
  dependencies need `--build`, code-only changes don't
- Built `/auth/login` as a thin proxy to Supabase's own token endpoint
  after losing track of test tokens twice — meant every future milestone's
  testing goes through the app's own API instead of raw Supabase calls
  with a manually-copied anon key
- Committed two response*.json files containing live (if short-lived, low-
  stakes) tokens before widening .gitignore to response*.json — caught
  both times via `git rm --cached`, not a rewritten history, since the
  tokens were test-scoped and already expired by the time it mattered
- PowerShell's curl.exe doesn't handle inline `-d "{...}"` with escaped
  quotes reliably — standardized on writing JSON to a file and using
  --data-binary "@file.json" for every POST/PATCH from here on

## 2026-09-11 — M2: metering path (idempotency, quota, cost calculation)

### Where AI helped
- Built CostCalculator as a pure function with unit tests first, before
  wiring it into any live endpoint — 7 tests covering each token type in
  isolation, zero-token edge case, truncation-not-rounding behavior made
  explicit, and a type guard against float creep. Verified against a real
  request afterward: 7 input + 249 output tokens on nexus-1-mini priced
  out to exactly 150 micros by hand, matching the endpoint's output
- Caught that quota checking needed a real plan attached to every org
  before it could mean anything — M1 never assigned one, since no
  billing flow existed yet. Fixed at the source (register() now defaults
  every new org to "free") and backfilled the three existing test orgs
  rather than leaving the gap for M2's tests to trip over
- Enforced idempotency at two layers, not one: an explicit pre-check
  (query by idempotency_key, return the stored result if found) for the
  common case, plus the database's own UNIQUE constraint on
  idempotency_key as the real guarantee — so even a race between two
  identical concurrent requests can produce at most one row, the second
  commit fails outright rather than silently double-counting
- Flagged the quota-check design honestly rather than presenting it as
  final: it queries usage_events directly for the current calendar month,
  not a pre-computed rollup (usage_rollups doesn't exist until M3). Real
  and correct for M2's gate, explicitly not the scalable version

### Where AI reordered the spec, and why
- The kickoff doc's numbered path lists "quota check" (step 6) before
  "simulate model response" (step 7). Built it the other way — mock
  response generated first, then quota checked against past usage PLUS
  this request's actual token count. The literal order would only let
  quota checking see history, never what the current request itself
  would consume, which weakens the guarantee for no benefit (mock
  generation carries no real cost or delay to justify deferring it)

### What I changed and why
- Idempotency-Key sent as an HTTP header (Stripe's own convention), not
  a request-body field — deliberate consistency with how M4's real
  Stripe webhook idempotency will work, so it's one pattern learned once
- Tested the over-quota gate by seeding one usage_event row directly via
  SQL (99,900 tokens) rather than sending ~1000 real requests to
  naturally exhaust a 100k quota — the resulting 429 showed used: 100156,
  correctly summing the seeded row AND the earlier real test request
  within the same period, not just the seed alone — stronger proof than
  a synthetic single-row test would have been
- pytest needed a pythonpath = . in pytest.ini — bare `pytest` doesn't
  put the project root (where app/ lives) on the import path by default,
  unlike uvicorn's module-invocation convention