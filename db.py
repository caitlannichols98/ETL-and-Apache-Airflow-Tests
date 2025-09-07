import psycopg2
import psycopg2.extras as extras
from typing import Iterable, Mapping
from .config import Settings

def get_conn(cfg: Settings):
    return psycopg2.connect(
        host=cfg.pg_host,
        port=cfg.pg_port,
        user=cfg.pg_user,
        password=cfg.pg_password,
        dbname=cfg.pg_database,
        application_name="yf_etl",
        connect_timeout=10
    )

def ensure_table(cfg: Settings):
    ddl = f"""
    CREATE TABLE IF NOT EXISTS {cfg.table_name} (
        ticker TEXT NOT NULL,
        week_start DATE NOT NULL,
        open_avg DOUBLE PRECISION,
        high_avg DOUBLE PRECISION,
        low_avg DOUBLE PRECISION,
        close_avg DOUBLE PRECISION,
        volume_avg BIGINT,
        open_median DOUBLE PRECISION,
        high_median DOUBLE PRECISION,
        low_median DOUBLE PRECISION,
        close_median DOUBLE PRECISION,
        volume_median BIGINT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (ticker, week_start)
    );
    """
    with get_conn(cfg) as conn, conn.cursor() as cur:
        cur.execute(ddl)
        conn.commit()

def upsert_rows(cfg: Settings, rows: Iterable[Mapping]):
    if not rows:
        return 0
    cols = [
        "ticker","week_start",
        "open_avg","high_avg","low_avg","close_avg","volume_avg",
        "open_median","high_median","low_median","close_median","volume_median"
    ]
    values = [[r.get(c) for c in cols] for r in rows]
    insert_sql = f"""
        INSERT INTO {cfg.table_name} ({", ".join(cols)})
        VALUES %s
        ON CONFLICT (ticker, week_start) DO UPDATE SET
          open_avg=EXCLUDED.open_avg,
          high_avg=EXCLUDED.high_avg,
          low_avg=EXCLUDED.low_avg,
          close_avg=EXCLUDED.close_avg,
          volume_avg=EXCLUDED.volume_avg,
          open_median=EXCLUDED.open_median,
          high_median=EXCLUDED.high_median,
          low_median=EXCLUDED.low_median,
          close_median=EXCLUDED.close_median,
          volume_median=EXCLUDED.volume_median;
    """
    with get_conn(cfg) as conn, conn.cursor() as cur:
        extras.execute_values(cur, insert_sql, values, page_size=1000)
        conn.commit()
    return len(values)
