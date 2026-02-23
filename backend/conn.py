import os
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv

load_dotenv()

SCHEMA = "ad_reference_dash"


def get_db_connection():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(f'SET search_path TO "{SCHEMA}"')
    cur.close()
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
        conn.close()
