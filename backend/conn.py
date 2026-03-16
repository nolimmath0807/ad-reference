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
    keepalives=1,
    keepalives_idle=30,
    keepalives_interval=10,
    keepalives_count=5,
)


def get_db_connection():
    conn = _pool.getconn()
    try:
        if conn.closed:
            _pool.putconn(conn, close=True)
            conn = _pool.getconn()
        cur = conn.cursor()
        cur.execute(f'SET search_path TO "{SCHEMA}", public')
        cur.close()
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        try:
            _pool.putconn(conn, close=True)
        except Exception:
            pass
        conn = _pool.getconn()
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
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            _pool.putconn(conn, close=conn.closed)
        except Exception:
            pass
