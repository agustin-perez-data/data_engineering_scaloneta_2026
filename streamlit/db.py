import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:"
            f"{os.environ['POSTGRES_PASSWORD']}@"
            f"{os.environ.get('POSTGRES_HOST', 'localhost')}:"
            f"{os.environ.get('POSTGRES_PORT', '5432')}/"
            f"{os.environ['POSTGRES_DB']}",
            pool_pre_ping=True,
            connect_args={"options": "-c client_encoding=UTF8"},
        )
    return _engine


def query(sql: str, params: dict = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)
