import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo
from .config import load_settings, Settings
from .db import ensure_table, upsert_rows

def _download_one(ticker: str, start: str | None, end: str | None) -> pd.DataFrame:
    # safer per-ticker pull reduces metadata flakiness
    df = yf.download(
        tickers=ticker,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,      # cleaner OHLC
        actions=False,         # ignore dividends/splits
        group_by="ticker",     # consistent columns
        threads=False,         # avoid rate-limit cascades
        progress=False,
    )
    # yfinance returns empty frame on failure; normalize to expected shape
    if df is None or df.empty:
        return pd.DataFrame(columns=["date","ticker","open","high","low","close","volume"])
    if isinstance(df.columns, pd.MultiIndex):
        # columns like ("Open", "AAPL"), ("Close","AAPL")
        df = df.stack(level=0, future_stack=True)  # <- silences pandas warning and is forward-safe
        df.index.set_names(["date","field"], inplace=True)
        df = df.reset_index().pivot(index="date", columns="field", values=0)
    else:
        # single-index columns like Open, High, ...
        pass
    df = df.rename(columns={
        "Open":"open", "High":"high", "Low":"low", "Close":"close",
        "Adj Close":"adj_close", "Volume":"volume"
    })
    df = df.reset_index().rename(columns={"Date":"date","Datetime":"date"})
    df["ticker"] = ticker
    # keep only the fields we actually use downstream
    keep = [c for c in ["date","ticker","open","high","low","close","volume"] if c in df.columns]
    return df[keep]

def extract(tickers: list[str], start: str | None, end: str | None) -> pd.DataFrame:
    parts = []
    for t in tickers:
        try:
            parts.append(_download_one(t, start, end))
        except Exception as e:
            # skip bad ticker/temporary metadata failure
            print(f"Skip {t}: {e}")
    if not parts:
        return pd.DataFrame(columns=["date","ticker","open","high","low","close","volume"])
    out = pd.concat(parts, ignore_index=True)
    # drop rows that are completely empty on price fields
    price_cols = [c for c in ["open","high","low","close","volume"] if c in out.columns]
    out = out.loc[out[price_cols].notna().any(axis=1)]
    return out

def transform(daily: pd.DataFrame, tz: str) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame(columns=[
            "ticker","week_start",
            "open_avg","high_avg","low_avg","close_avg","volume_avg",
            "open_median","high_median","low_median","close_median","volume_median"
        ])
    # ensure tz-aware, then convert to requested tz
    if not pd.api.types.is_datetime64_any_dtype(daily["date"]):
        daily["date"] = pd.to_datetime(daily["date"], utc=True, errors="coerce")
    daily = daily.dropna(subset=["date"]).copy()
    # convert timezone if provided
    try:
        daily["date"] = daily["date"].dt.tz_convert(ZoneInfo(tz))
    except Exception:
        daily["date"] = daily["date"].dt.tz_convert(ZoneInfo("UTC"))
    # normalize to date for week bucketing
    daily["date"] = daily["date"].dt.tz_localize(None)
    # Monday week start
    daily["week_start"] = daily["date"] - pd.to_timedelta(daily["date"].dt.weekday, unit="D")
    # aggregate
    agg_mean = daily.groupby(["ticker","week_start"], as_index=False).agg(
        open_avg=("open","mean"),
        high_avg=("high","mean"),
        low_avg=("low","mean"),
        close_avg=("close","mean"),
        volume_avg=("volume","mean"),
    )
    agg_med = daily.groupby(["ticker","week_start"], as_index=False).agg(
        open_median=("open","median"),
        high_median=("high","median"),
        low_median=("low","median"),
        close_median=("close","median"),
        volume_median=("volume","median"),
    )
    weekly = pd.merge(agg_mean, agg_med, on=["ticker","week_start"], how="inner").sort_values(
        ["ticker","week_start"]
    )
    # round and cast volumes to Int64
    if "volume_avg" in weekly:
        weekly["volume_avg"] = weekly["volume_avg"].round().astype("Int64")
    if "volume_median" in weekly:
        weekly["volume_median"] = weekly["volume_median"].round().astype("Int64")
    return weekly.reset_index(drop=True)

def load(cfg: Settings, weekly: pd.DataFrame) -> int:
    if weekly.empty:
        return 0
    ensure_table(cfg)
    rows = weekly.to_dict(orient="records")
    return upsert_rows(cfg, rows)

def main():
    cfg = load_settings()
    daily = extract(cfg.tickers, cfg.start_date, cfg.end_date)
    weekly = transform(daily, cfg.timezone)
    inserted = load(cfg, weekly)
    print(f"Upserted rows: {inserted}")

if __name__ == "__main__":
    sys.exit(main())
