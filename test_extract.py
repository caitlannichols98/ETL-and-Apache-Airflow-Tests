from app import etl

def test_extract_monkeypatched(monkeypatch):
    # stub yfinance.download to avoid network
    def fake_download(tickers, start, end, interval, auto_adjust, group_by, threads, progress):
        import pandas as pd
        idx = pd.date_range("2024-02-01", periods=3, freq="D", tz="UTC")
        df = pd.DataFrame({
            ("Open","AAPL"): [1,2,3],
            ("High","AAPL"): [2,3,4],
            ("Low","AAPL"):  [0,1,2],
            ("Close","AAPL"):[1.5,2.5,3.5],
            ("Volume","AAPL"):[10,20,30],
        }, index=idx)
        return df
    monkeypatch.setattr(etl.yf, "download", fake_download)
    out = etl.extract(["AAPL"], "2024-01-01", None)
    assert set(out.columns) == {"date","ticker","open","high","low","close","volume"}
    assert out["ticker"].nunique() == 1
    assert len(out) == 3
