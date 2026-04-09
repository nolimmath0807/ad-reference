import uuid
from datetime import date, datetime


def serialize_value(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


def serialize_row(cols: list[str], row: tuple) -> dict:
    return {col: serialize_value(val) for col, val in zip(cols, row)}


def rows_to_dicts(cur) -> list[dict]:
    cols = [desc[0] for desc in cur.description]
    return [serialize_row(cols, row) for row in cur.fetchall()]
