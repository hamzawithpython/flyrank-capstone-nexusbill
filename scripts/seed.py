import os
import secrets
import hashlib
import uuid
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:dev@db:5432/nexusbill")

PLANS = [
    # name, display_name, monthly_price_cents, api_call_quota, token_quota, rate_limit_rpm
    ("free", "Free", 0, 1000, 100000, 60),
    ("pro", "Pro", 2000, 50000, 5000000, 600),
    ("enterprise", "Enterprise", 9900, -1, -1, 6000),
]

MODELS = [
    # slug, display_name, input, cached_input, output, reasoning (all per-1M in micros)
    ("nexus-1", "Nexus 1", 3_000_000, 300_000, 15_000_000, 15_000_000),
    ("nexus-1-mini", "Nexus 1 Mini", 150_000, 15_000, 600_000, 600_000),
    ("nexus-2", "Nexus 2", 8_000_000, 800_000, 24_000_000, 24_000_000),
]


def seed_plans_and_models(conn):
    with conn.cursor() as cur:
        for name, display_name, price_cents, api_quota, token_quota, rpm in PLANS:
            cur.execute(
                """
                INSERT INTO plans (name, display_name, monthly_price_cents, api_call_quota, token_quota, rate_limit_rpm)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
                """,
                (name, display_name, price_cents, api_quota, token_quota, rpm),
            )
        for slug, display_name, input_p, cached_p, output_p, reasoning_p in MODELS:
            cur.execute(
                """
                INSERT INTO models (slug, display_name, input_price_per_1m_micros,
                                     cached_input_price_per_1m_micros, output_price_per_1m_micros,
                                     reasoning_price_per_1m_micros)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO NOTHING
                """,
                (slug, display_name, input_p, cached_p, output_p, reasoning_p),
            )
    conn.commit()
    print("Seed complete: 3 plans, 3 models.")


def seed_demo_org_and_key(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM organizations WHERE name = 'Demo Org'")
        if cur.fetchone():
            print("Demo org already seeded, skipping.")
            return

        cur.execute("SELECT id FROM plans WHERE name = 'free'")
        free_plan_id = cur.fetchone()[0]

        # Demo org has no real Supabase user behind it — it exists purely
        # so a stranger can call the API-key-authenticated billable
        # endpoint without registering. JWT-authenticated routes (org
        # management, project CRUD) still require a real account, since
        # those genuinely need a real Supabase-verified identity.
        demo_owner_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO organizations (owner_user_id, name, email, plan_id, status) "
            "VALUES (%s, 'Demo Org', 'demo@nexusbill.local', %s, 'active') RETURNING id",
            (demo_owner_id, free_plan_id),
        )
        org_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO projects (org_id, name, description) VALUES (%s, 'Demo Project', 'Seeded for evaluators — no signup required') RETURNING id",
            (org_id,),
        )
        project_id = cur.fetchone()[0]

        full_key = f"nb_live_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        key_prefix = full_key[:12]
        cur.execute(
            "INSERT INTO api_keys (project_id, key_hash, key_prefix, name, status) VALUES (%s, %s, %s, 'Demo Key', 'active')",
            (project_id, key_hash, key_prefix),
        )
        conn.commit()

        print("\n" + "=" * 60)
        print("DEMO API KEY (shown once — save it, not stored anywhere):")
        print(full_key)
        print("Try it:")
        print("curl -X POST http://localhost:8000/v1/chat/completions \\")
        print('  -H "Authorization: Bearer ' + full_key + '" \\')
        print('  -H "Idempotency-Key: demo-001" -H "Content-Type: application/json" \\')
        print('  -d \'{"model":"nexus-1-mini","messages":[{"role":"user","content":"hi"}]}\'')
        print("=" * 60 + "\n")


def main():
    conn = psycopg.connect(DATABASE_URL)
    seed_plans_and_models(conn)
    seed_demo_org_and_key(conn)
    conn.close()


if __name__ == "__main__":
    main()