from __future__ import annotations

INSTRUMENT_ENC: dict[str, int] = {
    "EURUSD": 0, "GBPUSD": 1, "USDJPY": 2, "XAUUSD": 3, "US500": 4,
    "CL": 5, "NG": 6, "NQ": 7, "RTY": 8, "YM": 9, "NKD": 10,
    "AUDUSD": 11, "AUDJPY": 12, "EURJPY": 13, "EURGBP": 14,
    "GBPJPY": 15, "USDCAD": 16, "USDCHF": 17, "USDMXN": 18,
}

_SESSION_QUALITY_ENC = {"high": 2, "medium": 1, "low": 0}
_DIRECTION_ENC = {"buy": 1, "sell": -1, "none": 0}

FEATURE_NAMES = [
    "ema_ratio", "rsi_14", "macd_hist", "atr_14",
    "session_quality_enc", "direction_enc", "signal_valid_enc",
    "ema_20", "ema_50", "macd", "macd_signal", "instrument_enc",
]


def build_feature_vector(record: dict, s3_key: str) -> list[float]:
    """Return a 12-element feature vector for a signal record."""
    ema_20 = float(record["ema_20"])
    ema_50 = float(record["ema_50"])
    return [
        ema_20 / ema_50,
        float(record["rsi_14"]),
        float(record["macd_hist"]),
        float(record["atr_14"]),
        _SESSION_QUALITY_ENC[record["session_quality"]],
        _DIRECTION_ENC[record["direction"]],
        int(bool(record["signal_valid"])),
        ema_20,
        ema_50,
        float(record["macd"]),
        float(record["macd_signal"]),
        INSTRUMENT_ENC[s3_key],
    ]
