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

_CLOSE_ON_RETURN = os.getenv("DB_CLOSE_ON_RETURN", "").lower() in ("true", "1", "yes")


def get_db_connection():
    max_retries = 5
    stale_retries = 0
    max_stale_retries = 20  # 풀의 모든 stale 커넥션을 순환할 수 있도록

    for attempt in range(max_retries + max_stale_retries):
        try:
            conn = _pool.getconn()
        except psycopg2.pool.PoolError:
            if attempt < max_retries - 1:
                logger.warning(f"Connection pool exhausted, retrying ({attempt + 1}/{max_retries})...")
                time.sleep(0.5 * (attempt + 1))
                continue
            logger.error("Connection pool exhausted after all retries")
            raise
        try:
            if conn.closed:
                _pool.putconn(conn, close=True)
                stale_retries += 1
                logger.warning(f"Closed connection discarded ({stale_retries}/{max_stale_retries})")
                continue
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.execute(f'SET search_path TO "{SCHEMA}", public')
            cur.close()
            return conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            try:
                _pool.putconn(conn, close=True)
            except Exception:
                pass
            stale_retries += 1
            logger.warning(f"Stale connection discarded ({stale_retries}/{max_stale_retries})")
            if stale_retries >= max_stale_retries:
                raise
            continue
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
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        # DB 연결 에러 시 커넥션 강제 닫기 (pool에서 제거됨)
        if isinstance(exc, (psycopg2.OperationalError, psycopg2.DatabaseError)):
            try:
                conn.close()
            except Exception:
                pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            _pool.putconn(conn, close=conn.closed or _CLOSE_ON_RETURN)
        except Exception:
            pass
