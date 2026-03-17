import logging
import os
import time
from contextlib import contextmanager

import psycopg2
import psycopg2.pool
from dotenv import load_dotenv

logger = logging.getLogger("conn")

load_dotenv()

SCHEMA = "ad_reference_dash"

_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=int(os.getenv("DB_POOL_MIN", "2")),
    maxconn=int(os.getenv("DB_POOL_MAX", "20")),
    dsn=os.environ["DATABASE_URL"],
    keepalives=1,
    keepalives_idle=30,
    keepalives_interval=10,
    keepalives_count=5,
)


def get_db_connection():
    retries = 5
    for attempt in range(retries):
        try:
            conn = _pool.getconn()
        except psycopg2.pool.PoolError:
            if attempt < retries - 1:
                logger.warning(f"Connection pool exhausted, retrying ({attempt + 1}/{retries})...")
                time.sleep(0.5 * (attempt + 1))
                continue
            logger.error("Connection pool exhausted after all retries")
            raise
        try:
            if conn.closed:
                _pool.putconn(conn, close=True)
                continue
            cur = conn.cursor()
            cur.execute(f'SET search_path TO "{SCHEMA}", public')
            cur.close()
            return conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            try:
                _pool.putconn(conn, close=True)
            except Exception:
                pass
            if attempt < retries - 1:
                logger.warning(f"Stale connection discarded, retrying ({attempt + 1}/{retries})...")
                continue
            raise
        except Exception:
            _pool.putconn(conn)
            raise
    raise psycopg2.pool.PoolError("Failed to get connection after retries")


@contextmanager
def get_db(statement_timeout: int | None = None):
    conn = get_db_connection()
    cur = conn.cursor()
    if statement_timeout is not None:
        cur.execute(f"SET statement_timeout = {statement_timeout}")
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
