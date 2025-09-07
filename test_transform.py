from app import etl

def test_transform_weekly(sample_daily_df):
    weekly = etl.transform(sample_daily_df, tz="UTC")
    assert {"ticker","week_start","close_avg","close_median"}.issubset(weekly.columns)
    assert weekly["week_start"].dt.weekday.eq(0).all()
    assert weekly["ticker"].nunique() == 1
    assert weekly["week_start"].is_monotonic_increasing
