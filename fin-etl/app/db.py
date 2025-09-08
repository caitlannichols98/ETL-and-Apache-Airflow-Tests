import psycopg2
import psycopg2.extras as extras
from typing import Iterable, Mapping
from .config import Settings

def get_conn(cfg: Settings):
    # simple, env-driven connection
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
    create table if not exists {cfg.table_name} (
        ticker text not null,
        week_start date not null,
        open_avg double precision,
        high_avg double precision,
        low_avg double precision,
        close_avg double precision,
        volume_avg bigint,
        open_median double precision,
        high_median double precision,
        low_median double precision,
        close_median double precision,
        volume_median bigint,
        primary key (ticker, week_start)
    );
    """
    with get_conn(cfg) as conn, conn.cursor() as cur:
        cur.execute(ddl)
        conn.commit()

def upsert_rows(cfg: Settings, rows: Iterable[Mapping]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    cols = [
        "ticker","week_start",
        "open_avg","high_avg","low_avg","close_avg","volume_avg",
        "open_median","high_median","low_median","close_median","volume_median"
    ]
    values = [[r.get(c) for c in cols] for r in rows]
    sql = f"""
    insert into {cfg.table_name} ({", ".join(cols)}) values %s
    on conflict (ticker, week_start) do update set
        open_avg=excluded.open_avg,
        high_avg=excluded.high_avg,
        low_avg=excluded.low_avg,
        close_avg=excluded.close_avg,
        volume_avg=excluded.volume_avg,
        open_median=excluded.open_median,
        high_median=excluded.high_median,
        low_median=excluded.low_median,
        close_median=excluded.close_median,
        volume_median=excluded.volume_median
    """
    with get_conn(cfg) as conn, conn.cursor() as cur:
        extras.execute_values(cur, sql, values, page_size=1000)
        conn.commit()
    return len(values)
