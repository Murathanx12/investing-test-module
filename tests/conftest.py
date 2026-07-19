import gzip
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _write_history(path: Path, start: str, end: str, seed: int, start_price: float = 20.0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end)
    rets = rng.normal(0.0004, 0.02, len(dates))
    close = start_price * np.exp(np.cumsum(rets))
    df = pd.DataFrame({
        "Date": dates.strftime("%Y-%m-%d"),
        "Open": close, "High": close * 1.01, "Low": close * 0.99,
        "Close": close, "Adjusted_close": close,
        "Volume": rng.integers(50_000, 500_000, len(dates)),
    })
    with gzip.open(path, "wt") as fh:
        df.to_csv(fh, index=False)


@pytest.fixture(scope="session")
def fake_archive(tmp_path_factory) -> Path:
    """Miniature EODHD-shaped archive: 8 active names + 2 that die mid-window."""
    root = tmp_path_factory.mktemp("eodhd")
    (root / "active").mkdir()
    (root / "delisted").mkdir()
    for i in range(8):
        _write_history(root / "active" / f"ACT{i}.csv.gz", "2017-01-02", "2020-12-31", seed=i)
    _write_history(root / "delisted" / "DEAD0.csv.gz", "2017-01-02", "2019-06-28", seed=100)
    _write_history(root / "delisted" / "DEAD1.csv.gz", "2017-01-02", "2018-03-30", seed=101)
    return root
