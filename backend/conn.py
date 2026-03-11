import os
from contextlib import contextmanager

import psycopg2
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

SCHEMA = "ad_reference_dash"

_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=int(os.getenv("DB_POOL_MIN", "2")),
    maxconn=int(os.getenv("DB_POOL_MAX", "10")),
    dsn=os.environ["DATABASE_URL"],
)


def get_db_connection():
    conn = _pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(f'SET search_path TO "{SCHEMA}", public')
        cur.close()
    except Exception:
        _pool.putconn(conn)
        raise
    return conn


@contextmanager
def get_db():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        _pool.putconn(conn)
