#!/usr/bin/env python3
"""
Fetch, normalize, and optionally load campground data from a single source.

CLI
---
    python run_single_source.py recreation_gov|nps [--limit N] [--load] [--dry-run]

Examples
--------
    # Fetch and normalise 10 records from Recreation.gov, print a sample
    python run_single_source.py recreation_gov --limit 10

    # Fetch from NPS and write to Firestore
    python run_single_source.py nps --load

    # Dry-run: gather stats without writing anything
    python run_single_source.py recreation_gov --dry-run
"""

import sys
from pathlib import Path

_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

import argparse
import json
import logging
from datetime import datetime, timezone

from sources.recreation_gov import RecreationGovSource
from sources.nps_api import NPSSource
from transforms.normalizer import normalize_recreation_gov, normalize_nps
from loaders.firestore_loader import FirestoreLoader
from config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("run_single_source")

SOURCE_MAP = {
    "recreation_gov": {
        "client_cls": RecreationGovSource,
        "normalizer": normalize_recreation_gov,
    },
    "nps": {
        "client_cls": NPSSource,
        "normalizer": normalize_nps,
    },
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch and normalise campground data from a single source.",
    )
    parser.add_argument(
        "source",
        choices=sorted(SOURCE_MAP.keys()),
        help="Data source to pull from.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of records to fetch (useful for testing).",
    )
    parser.add_argument(
        "--load",
        action="store_true",
        default=False,
        help="Write normalised records to Firestore.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print stats without writing to Firestore.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    source_name = args.source
    source_cfg = SOURCE_MAP[source_name]

    logger.info("=== run_single_source: %s ===", source_name)
    start_time = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # 1. Fetch
    # ------------------------------------------------------------------
    logger.info("Initialising %s client ...", source_name)
    client = source_cfg["client_cls"]()
    normalizer = source_cfg["normalizer"]

    raw_records = []
    logger.info("Fetching campgrounds (limit=%s) ...", args.limit)
    for idx, record in enumerate(client.fetch_all_campgrounds()):
        if args.limit is not None and idx >= args.limit:
            break
        raw_records.append(record)

    logger.info("Fetched %d raw records from %s.", len(raw_records), source_name)

    # ------------------------------------------------------------------
    # 2. Normalise
    # ------------------------------------------------------------------
    normalized = []
    errors = 0
    for record in raw_records:
        try:
            normalized.append(normalizer(record))
        except Exception as exc:
            errors += 1
            logger.warning("Normalisation error: %s", exc)

    logger.info(
        "Normalised %d records (%d errors).",
        len(normalized),
        errors,
    )

    # ------------------------------------------------------------------
    # 3. Load / dry-run / sample output
    # ------------------------------------------------------------------
    if args.dry_run:
        logger.info("--- DRY-RUN STATS ---")
        logger.info("Source:           %s", source_name)
        logger.info("Raw fetched:     %d", len(raw_records))
        logger.info("Normalised:      %d", len(normalized))
        logger.info("Errors:          %d", errors)
        if normalized:
            sample = normalized[0]
            logger.info(
                "Sample record:\n%s",
                json.dumps(
                    {k: v for k, v in sample.items() if k != "location" or True},
                    indent=2,
                    default=str,
                ),
            )

    elif args.load:
        logger.info("Loading %d records into Firestore ...", len(normalized))
        loader = FirestoreLoader()
        result = loader.upsert_batch(normalized)
        logger.info("Firestore upsert result: %s", result)

    else:
        # Default: print a sample of the normalised output
        logger.info("No --load or --dry-run flag; printing sample output.")
        sample_size = min(3, len(normalized))
        for i, record in enumerate(normalized[:sample_size]):
            print(f"\n--- Record {i + 1}/{sample_size} ---")
            print(json.dumps(record, indent=2, default=str))
        if len(normalized) > sample_size:
            print(f"\n... and {len(normalized) - sample_size} more records.")

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("Finished in %.1f s.", elapsed)


if __name__ == "__main__":
    main()
