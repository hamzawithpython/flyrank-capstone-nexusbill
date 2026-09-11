# NexusBill — Job Card

## What it does
Usage-based billing infrastructure for an AI API product. Meters every
billable request, enforces quota limits before they're exceeded, computes
exact per-request cost, and syncs subscription state with Stripe — the
layer a company selling AI API access needs between "someone called our
API" and "we billed them correctly for it."

## Input
- `POST /v1/chat/completions` — API key + model + messages. Simulates an
  AI completion (no real model call) to exercise the full metering path.
- `POST /billing/checkout` — JWT + target plan name.
- `POST /webhooks/stripe` — raw Stripe event payload + signature header.

## Output
- A metered usage event, an exact cost in microdollars, and either a
  successful completion or a 429 with quota details.
- A Stripe-hosted checkout session URL.
- Webhook acknowledgment (always 200) with internal state updated
  (subscription synced, plan changed, or failure recorded for retry).

## Must-never rules
- Never store a plaintext API key — only its SHA-256 hash and a short
  prefix for display. The full key is shown exactly once, at creation.
- Never let a request bypass quota enforcement — the check happens before
  any usage is recorded, not after.
- Never process a Stripe webhook without verifying its signature first —
  invalid signature means nothing gets written, ever.
- Never recompute a historical cost — pricing is pinned at write time;
  changing today's prices must never alter yesterday's bills.
- Never let one org's query return another org's data — every query
  touching org-scoped tables filters by `org_id` derived from the
  caller's own credential, never from a client-supplied ID alone.