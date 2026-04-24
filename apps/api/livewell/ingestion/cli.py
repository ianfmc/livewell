"""CLI entry point for running ingestion manually or from cron."""
from __future__ import annotations

import argparse
import logging

from livewell.ingestion.ingest import run_ingestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OHLCV data to S3")
    parser.add_argument(
        "--instruments",
        nargs="*",
        help="S3 key names to ingest (e.g. EURUSD GBPUSD). Defaults to all.",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Fetch full 2-year history instead of incremental update.",
    )
    args = parser.parse_args()
    result = run_ingestion(instruments=args.instruments, backfill=args.backfill)
    if result["failed"]:
        raise SystemExit(f"Failed instruments: {result['failed']}")


if __name__ == "__main__":
    main()
