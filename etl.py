import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo
from .config import load_settings
from .db import ensure_table, upsert_rows

def extract(tickers: list[str], start: str | None, end: str | None) -> pd.DataFrame:
    df = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        threads=True,
        progress=False
    )
    if isinstance(df.columns, pd.MultiIndex):
        df = df.stack(0).rename_axis(index=["date","ticker"]).reset_index()
    else:
        df["ticker"] = tickers[0]
        df = df.rename_axis(index="date").reset_index()
    return df[["date","ticker","Open","High","Low","Close","Volume"]].rename(
        columns=str.lower
    )

def transform(daily: pd.DataFrame, tz: str) -> pd.DataFrame:
    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"], utc=True)
    daily["date"] = daily["date"].dt.tz_convert(ZoneInfo(tz)).dt.tz_localize(None)
    daily["week_start"] = daily["date"] - pd.to_timedelta(daily["date"].dt.weekday, unit="D")
    agg_mean = daily.groupby(["ticker","week_start"], as_index=False).agg(
        open_avg=("open","mean"),
        high_avg=("high","mean"),
        low_avg=("low","mean"),
        close_avg=("close","mean"),
        volume_avg=("volume","mean")
    )
    agg_med = daily.groupby(["ticker","week_start"], as_index=False).agg(
        open_median=("open","median"),
        high_median=("high","median"),
        low_median=("low","median"),
        close_median=("close","median"),
        volume_median=("volume","median")
    )
    weekly = pd.merge(agg_mean, agg_med, on=["ticker","week_start"], how="inner")
    weekly = weekly.sort_values(["ticker","week_start"]).reset_index(drop=True)
    # cast volumes to int
    weekly["volume_avg"] = weekly["volume_avg"].round().astype("Int64")
    weekly["volume_median"] = weekly["volume_median"].round().astype("Int64")
    return weekly

def load(cfg, weekly: pd.DataFrame) -> int:
    ensure_table(cfg)
    rows = weekly.to_dict(orient="records")
    return upsert_rows(cfg, rows)

def main():
    cfg = load_settings()
    tickers = cfg.tickers
    daily = extract(tickers, cfg.start_date, cfg.end_date)
    weekly = transform(daily, cfg.timezone)
    inserted = load(cfg, weekly)
    print(f"Upserted rows: {inserted}")

if __name__ == "__main__":
    sys.exit(main())
