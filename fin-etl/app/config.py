import os
from dataclasses import dataclass

@dataclass
class Settings:
    pg_host: str
    pg_port: int
    pg_user: str
    pg_password: str
    pg_database: str
    table_name: str
    tickers: list[str]
    start_date: str | None
    end_date: str | None
    timezone: str

def _parse_tickers(raw: str | None) -> list[str]:
    if not raw:
        return ["AAPL","MSFT"]
    return [t.strip().upper() for t in raw.split(",") if t.strip()]

def _safe_table_name(name: str) -> str:
    assert name.replace("_","").isalnum(), "TABLE_NAME must be alnum and underscores only"
    return name

def load_settings() -> Settings:
    return Settings(
        pg_host=os.getenv("PGHOST","127.0.0.1"),
        pg_port=int(os.getenv("PGPORT","5432")),
        pg_user=os.getenv("PGUSER","etl"),
        pg_password=os.getenv("PGPASSWORD",""),
        pg_database=os.getenv("PGDATABASE","market"),
        table_name=_safe_table_name(os.getenv("TABLE_NAME","yf_weekly_ohlcv")),
        tickers=_parse_tickers(os.getenv("TICKERS")),
        start_date=os.getenv("START_DATE"),
        end_date=os.getenv("END_DATE") or None,
        timezone=os.getenv("TZ","UTC"),
    )
