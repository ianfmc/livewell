"""Indicator config and pandas-ta column rename map."""

PRICES_PREFIX = "prices"
FEATURES_PREFIX = "features"

FEATURE_COLUMNS = ["date", "ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"]

# pandas-ta default names → our snake_case names
COLUMN_RENAMES = {
    "EMA_20":        "ema_20",
    "EMA_50":        "ema_50",
    "RSI_14":        "rsi_14",
    "MACD_12_26_9":  "macd",
    "MACDh_12_26_9": "macd_hist",
    "MACDs_12_26_9": "macd_signal",
    "ATRr_14":       "atr_14",
}
