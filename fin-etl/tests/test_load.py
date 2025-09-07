import os
import psycopg2
import pandas as pd
from app.config import Settings
from app.db import ensure_table
from app.etl import load as etl_load

def _conn_from_url(url: str):
    import urllib.parse as up
    p = up.urlparse(url)
    return dict(
        host=p.hostname, port=p.port or 5432, user=p.username,
        password=p.password, dbname=p.path.lstrip("/")
    )

def test_load_integration(sample_daily_df, monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        import pytest
        pytest.skip("TEST_DATABASE_URL not set")
    params = _conn_from_url(url)
    table = "yf_weekly_ohlcv_test"
    cfg = Settings(
        pg_host=params["host"], pg_port=int(params["port"]), pg_user=params["user"],
        pg_password=params["password"], pg_database=params["dbname"],
        table_name=table, tickers=["TEST"], start_date=None, end_date=None, timezone="UTC"
    )
    weekly = pd.DataFrame({
        "ticker":["TEST","TEST"],
        "week_start": pd.to_datetime(["2024-01-01","2024-01-08"]).date,
        "open_avg":[1.0,2.0],"high_avg":[1.1,2.1],"low_avg":[0.9,1.9],"close_avg":[1.05,2.05],
        "volume_avg":[100,200],
        "open_median":[1.0,2.0],"high_median":[1.1,2.1],"low_median":[0.9,1.9],"close_median":[1.05,2.05],
        "volume_median":[100,200]
    })
    ensure_table(cfg)
    n = etl_load(cfg, weekly)
    assert n == 2

    with psycopg2.connect(**params) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s ORDER BY column_name", (table,))
        cols = dict(cur.fetchall())
        for c in ["ticker","week_start","close_avg","volume_median"]:
            assert c in cols
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        total = cur.fetchone()[0]
        assert total >= 2
