import os
from sqlmodel import create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:dev@db:5432/nexusbill")

# SQLAlchemy defaults a plain postgresql:// URL to psycopg2, which isn't
# installed — we intentionally use psycopg3 (psycopg[binary]) instead.
# Tell SQLAlchemy explicitly, without touching DATABASE_URL itself (raw
# psycopg.connect() calls elsewhere — migrations, seed — expect the plain form).
SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as session:
        yield session