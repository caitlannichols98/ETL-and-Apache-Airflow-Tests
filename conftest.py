import os
import pandas as pd
import numpy as np
import pytest

@pytest.fixture
def sample_daily_df():
    rng = pd.date_range("2024-01-01", periods=30, freq="D", tz="UTC")
    data = {
        "date": rng,
        "ticker": ["TEST"]*len(rng),
        "open": np.linspace(100, 120, len(rng)),
        "high": np.linspace(101, 121, len(rng)),
        "low":  np.linspace( 99, 119, len(rng)),
        "close":np.linspace(100.5, 120.5, len(rng)),
        "volume": np.random.randint(1_000_000, 2_000_000, len(rng))
    }
    return pd.DataFrame(data)

def require_test_db():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set, skipping DB integration test")
