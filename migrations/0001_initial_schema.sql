-- 0001_initial_schema.sql
-- NexusBill core schema.

CREATE TABLE plans (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                  TEXT NOT NULL,
    display_name          TEXT NOT NULL,
    monthly_price_cents   INTEGER NOT NULL,
    api_call_quota        INTEGER NOT NULL,
    token_quota           INTEGER NOT NULL,
    rate_limit_rpm        INTEGER NOT NULL
);

CREATE TABLE organizations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    email               TEXT NOT NULL UNIQUE,
    stripe_customer_id  TEXT UNIQUE,
    plan_id             UUID REFERENCES plans(id),
    status              TEXT NOT NULL CHECK (status IN ('active','suspended','cancelled')) DEFAULT 'active',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    name            TEXT NOT NULL,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at     TIMESTAMPTZ
);

CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    key_hash        TEXT NOT NULL UNIQUE,
    key_prefix      TEXT NOT NULL,
    name            TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('active','revoked')) DEFAULT 'active',
    last_used_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at      TIMESTAMPTZ
);

CREATE TABLE models (
    id                                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                                TEXT NOT NULL UNIQUE,
    display_name                        TEXT NOT NULL,
    input_price_per_1m_micros           BIGINT NOT NULL,
    cached_input_price_per_1m_micros    BIGINT NOT NULL,
    output_price_per_1m_micros          BIGINT NOT NULL,
    reasoning_price_per_1m_micros       BIGINT NOT NULL,
    is_active                           BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE usage_events (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                UUID NOT NULL REFERENCES organizations(id),
    project_id            UUID NOT NULL REFERENCES projects(id),
    api_key_id            UUID NOT NULL REFERENCES api_keys(id),
    model_id              UUID NOT NULL REFERENCES models(id),
    idempotency_key       TEXT NOT NULL UNIQUE,
    input_tokens          INTEGER NOT NULL,
    cached_input_tokens   INTEGER NOT NULL DEFAULT 0,
    output_tokens         INTEGER NOT NULL,
    reasoning_tokens      INTEGER NOT NULL DEFAULT 0,
    total_cost_micros     BIGINT NOT NULL,
    request_duration_ms   INTEGER,
    endpoint              TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE usage_rollups (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                UUID NOT NULL REFERENCES organizations(id),
    period_start          DATE NOT NULL,
    period_end            DATE NOT NULL,
    api_calls             INTEGER NOT NULL DEFAULT 0,
    input_tokens          BIGINT NOT NULL DEFAULT 0,
    cached_input_tokens   BIGINT NOT NULL DEFAULT 0,
    output_tokens         BIGINT NOT NULL DEFAULT 0,
    reasoning_tokens      BIGINT NOT NULL DEFAULT 0,
    total_cost_micros     BIGINT NOT NULL DEFAULT 0,
    computed_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id, period_start)
);

CREATE TABLE subscriptions (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                   UUID NOT NULL UNIQUE REFERENCES organizations(id),
    plan_id                  UUID NOT NULL REFERENCES plans(id),
    stripe_subscription_id   TEXT UNIQUE,
    stripe_price_id          TEXT,
    status                   TEXT NOT NULL CHECK (status IN ('active','past_due','cancelled','trialing')),
    current_period_start     TIMESTAMPTZ,
    current_period_end       TIMESTAMPTZ,
    cancelled_at             TIMESTAMPTZ,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE stripe_webhook_events (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_event_id   TEXT NOT NULL UNIQUE,
    event_type        TEXT NOT NULL,
    payload           JSONB NOT NULL,
    status            TEXT NOT NULL CHECK (status IN ('pending','processed','failed')) DEFAULT 'pending',
    attempts          INTEGER NOT NULL DEFAULT 0,
    last_error        TEXT,
    processed_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only. Application code must never UPDATE or DELETE rows here.
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id),
    actor           TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    payload         JSONB,
    ip_address      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reconciliation_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    orgs_checked    INTEGER NOT NULL,
    mismatches      JSONB,
    status          TEXT NOT NULL CHECK (status IN ('clean','has_mismatches'))
);

CREATE TABLE usage_alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    alert_type      TEXT NOT NULL CHECK (alert_type IN ('quota_80','quota_100')),
    usage_type      TEXT NOT NULL CHECK (usage_type IN ('api_calls','tokens')),
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    period_start    DATE NOT NULL,
    UNIQUE (org_id, alert_type, usage_type, period_start)
);

-- Foreign key columns aren't auto-indexed in Postgres (unlike primary keys).
-- These four get hit on every metering request and every rollup/reconciliation run.
CREATE INDEX idx_usage_events_org_id ON usage_events(org_id);
CREATE INDEX idx_usage_events_project_id ON usage_events(project_id);
CREATE INDEX idx_api_keys_project_id ON api_keys(project_id);
CREATE INDEX idx_audit_log_org_id ON audit_log(org_id);