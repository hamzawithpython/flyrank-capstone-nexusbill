import os
import psycopg

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:dev@db:5432/nexusbill")

def get_applied(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        conn.commit()
        cur.execute("SELECT filename FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}

def apply_migration(conn, filepath, filename):
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (filename,))
    conn.commit()
    print(f"Applied {filename}")

def main():
    conn = psycopg.connect(DATABASE_URL)
    applied = get_applied(conn)
    files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
    ran_any = False
    for filename in files:
        if filename in applied:
            print(f"Skipping {filename} (already applied)")
            continue
        apply_migration(conn, os.path.join(MIGRATIONS_DIR, filename), filename)
        ran_any = True
    if not ran_any:
        print("All migrations already applied.")
    conn.close()

if __name__ == "__main__":
    main()