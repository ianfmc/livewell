from livewell.ingestion.constants import INSTRUMENTS, INTERVALS, S3_PREFIX


def test_instruments_count():
    assert len(INSTRUMENTS) == 5


def test_instruments_have_required_keys():
    for inst in INSTRUMENTS:
        assert "name" in inst
        assert "ticker" in inst
        assert "s3_key" in inst


def test_intervals():
    assert set(INTERVALS.keys()) == {"1d", "1h"}
    assert INTERVALS["1d"]["lookback_days"] == 7
    assert INTERVALS["1h"]["lookback_days"] == 30
    assert INTERVALS["1d"]["backfill_years"] == 2
    assert INTERVALS["1h"]["backfill_years"] == 2


def test_s3_prefix():
    assert S3_PREFIX == "prices"
