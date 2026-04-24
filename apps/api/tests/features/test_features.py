import numpy as np
from unittest.mock import patch
import boto3
import pandas as pd
import pytest
from moto import mock_aws

from livewell.features.constants import FEATURE_COLUMNS, PRICES_PREFIX, FEATURES_PREFIX, COLUMN_RENAMES


def test_feature_columns():
    assert FEATURE_COLUMNS == ["date", "ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"]


def test_prefixes():
    assert PRICES_PREFIX == "prices"
    assert FEATURES_PREFIX == "features"


def test_column_renames_maps_all_indicators():
    expected_targets = {"ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"}
    assert set(COLUMN_RENAMES.values()) == expected_targets
