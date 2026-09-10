# scripts/seed.py
import os
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

def main():
    conn = psycopg.connect(DATABASE_URL)
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
    conn.close()
    print("Seed complete: 3 plans, 3 models.")

if __name__ == "__main__":
    main()