"""
etl/load/db.py
---------------
SQLAlchemy engine factory for the scaloneta2026 PostgreSQL database.

Environment variables (loaded from .env via python-dotenv):
    POSTGRES_USER
    POSTGRES_PASSWORD
    POSTGRES_HOST
    POSTGRES_PORT
    POSTGRES_DB

Usage:
    from etl.load.db import get_engine, query

    engine = get_engine()

    df = query("SELECT * FROM dim_player WHERE position = :pos", {"pos": "GK"})
"""

from __future__ import annotations

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()

_engine: Engine | None = None


def get_engine() -> Engine:
    """
    Return a singleton SQLAlchemy engine.

    The engine is created once and reused for the process lifetime.
    pool_pre_ping=True will verify connections before use (handles
    reconnects after the DB container restarts).
    """
    global _engine
    if _engine is None:
        user = os.environ["POSTGRES_USER"]
        password = os.environ["POSTGRES_PASSWORD"]
        host = os.environ["POSTGRES_HOST"]
        port = os.environ["POSTGRES_PORT"]
        db = os.environ["POSTGRES_DB"]

        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
        _engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"options": "-c client_encoding=UTF8"},
        )

    return _engine


def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """
    Execute a SELECT query and return results as a DataFrame.

    Args:
        sql:    SQL string, may contain :param_name placeholders.
        params: Optional dict of bind parameters.

    Returns:
        pd.DataFrame with query results.
    """
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})
