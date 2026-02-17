#!/usr/bin/env python3
"""
Full campground data sync pipeline.

Fetches from all API sources and scrapers, deduplicates, and loads
into Firestore in a single coordinated run.

CLI
---
    python run_full_sync.py [--dry-run] [--skip-scrapers]

Phases
------
1. Fetch + normalise from Recreation.gov
2. Fetch + normalise from NPS
3. Run all Scrapy spiders and collect results (unless --skip-scrapers)
4. Cross-source deduplication across all sources
5. Batch upsert to Firestore
6. Soft-delete stale records
"""

import sys
from pathlib import Path

_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

import argparse
import logging
from datetime import datetime, timezone

from tqdm import tqdm

from sources.recreation_gov import RecreationGovSource
from sources.nps_api import NPSSource
from transforms.normalizer import normalize_recreation_gov, normalize_nps, normalize_scraped
from transforms.deduplicator import find_duplicates, resolve_duplicates
from loaders.firestore_loader import FirestoreLoader
from config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("run_full_sync")

# Spiders that will be executed in Phase 3
ALL_SPIDERS = ["koa", "hipcamp", "good_sam", "thousand_trails", "state_parks"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the full campground data sync pipeline.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Log what would happen without writing to Firestore.",
    )
    parser.add_argument(
        "--skip-scrapers",
        action="store_true",
        default=False,
        help="Skip Phase 3 (Scrapy spiders).",
    )
    return parser


# ------------------------------------------------------------------
# Phase helpers
# ------------------------------------------------------------------

def _phase1_recreation_gov() -> list:
    """Fetch and normalise all campgrounds from Recreation.gov."""
    logger.info("Phase 1: Fetching from Recreation.gov ...")
    client = RecreationGovSource()
    raw_records = list(client.fetch_all_campgrounds())
    logger.info("  Fetched %d raw records.", len(raw_records))

    normalized = []
    errors = 0
    for record in tqdm(raw_records, desc="Normalising Recreation.gov", unit="rec"):
        try:
            normalized.append(normalize_recreation_gov(record))
        except Exception as exc:
            errors += 1
            logger.warning("  Normalisation error: %s", exc)

    logger.info(
        "  Phase 1 complete: %d normalised, %d errors.",
        len(normalized),
        errors,
    )
    return normalized


def _phase2_nps() -> list:
    """Fetch and normalise all campgrounds from the NPS API."""
    logger.info("Phase 2: Fetching from NPS ...")
    client = NPSSource()
    raw_records = list(client.fetch_all_campgrounds())
    logger.info("  Fetched %d raw records.", len(raw_records))

    normalized = []
    errors = 0
    for record in tqdm(raw_records, desc="Normalising NPS", unit="rec"):
        try:
            normalized.append(normalize_nps(record))
        except Exception as exc:
            errors += 1
            logger.warning("  Normalisation error: %s", exc)

    logger.info(
        "  Phase 2 complete: %d normalised, %d errors.",
        len(normalized),
        errors,
    )
    return normalized


def _phase3_scrapers() -> list:
    """Run all Scrapy spiders and collect normalised items.

    Uses ``scrapy.crawler.CrawlerProcess`` to execute spiders in-process.
    Items are captured via a custom pipeline that appends to a shared list.
    """
    logger.info("Phase 3: Running Scrapy spiders ...")

    # Import Scrapy here so the rest of the pipeline can run without it
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    collected_items: list = []

    class _CollectorPipeline:
        """Lightweight pipeline that normalises items and stores them."""

        def process_item(self, item, spider):
            try:
                source_name = getattr(spider, "source_name", spider.name)
                normalised = normalize_scraped(dict(item), source_name)
                collected_items.append(normalised)
            except Exception as exc:
                logger.warning(
                    "  Normalisation error in spider %s: %s", spider.name, exc
                )
            return item

    # Build Scrapy settings from the project, then override pipelines so
    # items flow into our collector instead of the default Firestore pipeline.
    scrapers_dir = Path(_backend_root) / "scrapers"
    sys.path.insert(0, str(scrapers_dir))

    scrapy_settings = get_project_settings()
    scrapy_settings.set("ITEM_PIPELINES", {
        f"{__name__}._CollectorPipeline": 100,
    })
    # Register the collector pipeline class so Scrapy can resolve the path
    scrapy_settings.set("ITEM_PIPELINES", {
        "campground_scrapers.pipelines.ValidationPipeline": 100,
    })

    # Replace pipelines with our collector by using a custom settings dict
    custom_settings = {
        "ITEM_PIPELINES": {
            "campground_scrapers.pipelines.ValidationPipeline": 100,
        },
        "LOG_LEVEL": settings.LOG_LEVEL,
    }
    scrapy_settings.setdict(custom_settings)

    process = CrawlerProcess(scrapy_settings)

    # Dynamically load and enqueue each spider
    spider_loader = process.spider_loader
    available = spider_loader.list()
    logger.info("  Available spiders: %s", available)

    for spider_name in ALL_SPIDERS:
        if spider_name in available:
            logger.info("  Enqueuing spider: %s", spider_name)
            spider_cls = spider_loader.load(spider_name)

            # Attach the collector pipeline at the spider level
            spider_cls.custom_settings = spider_cls.custom_settings or {}
            spider_cls.custom_settings["ITEM_PIPELINES"] = {
                f"{_CollectorPipeline.__module__}.{_CollectorPipeline.__qualname__}": 800,
                "campground_scrapers.pipelines.ValidationPipeline": 100,
            }
            process.crawl(spider_cls)
        else:
            logger.warning("  Spider '%s' not found, skipping.", spider_name)

    # CrawlerProcess.start() blocks until all spiders finish.
    # install_signal_handlers=False lets us run inside scripts safely.
    process.start(install_signal_handlers=False)

    logger.info("  Phase 3 complete: collected %d items.", len(collected_items))
    return collected_items


def _phase4_dedup(all_records: list) -> list:
    """Cross-source deduplication."""
    logger.info("Phase 4: Deduplication across %d records ...", len(all_records))
    dup_pairs = find_duplicates(all_records)
    logger.info("  Found %d duplicate pairs.", len(dup_pairs))
    deduped = resolve_duplicates(all_records, dup_pairs)
    logger.info(
        "  After dedup: %d records (removed %d).",
        len(deduped),
        len(all_records) - len(deduped),
    )
    return deduped


def _phase5_upsert(records: list, dry_run: bool) -> dict:
    """Batch upsert to Firestore."""
    logger.info("Phase 5: Upserting %d records (dry_run=%s) ...", len(records), dry_run)
    loader = FirestoreLoader()
    result = loader.upsert_batch(records, dry_run=dry_run)
    logger.info("  Upsert result: %s", result)
    return result


def _phase6_stale(active_doc_ids: set, dry_run: bool) -> int:
    """Soft-delete stale records no longer present in the pipeline."""
    logger.info("Phase 6: Deactivating stale records (dry_run=%s) ...", dry_run)
    loader = FirestoreLoader()
    count = loader.delete_stale_records(active_doc_ids, dry_run=dry_run)
    logger.info("  Deactivated %d stale records.", count)
    return count


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    args = _build_parser().parse_args()
    start_time = datetime.now(timezone.utc)
    logger.info("=== Full sync started at %s ===", start_time.isoformat())

    all_records: list = []

    # Phase 1
    all_records.extend(_phase1_recreation_gov())

    # Phase 2
    all_records.extend(_phase2_nps())

    # Phase 3
    if args.skip_scrapers:
        logger.info("Phase 3: SKIPPED (--skip-scrapers)")
    else:
        all_records.extend(_phase3_scrapers())

    logger.info("Total records before dedup: %d", len(all_records))

    # Phase 4
    deduped = _phase4_dedup(all_records)

    # Phase 5
    _phase5_upsert(deduped, dry_run=args.dry_run)

    # Phase 6
    active_ids = {r["_doc_id"] for r in deduped if r.get("_doc_id")}
    _phase6_stale(active_ids, dry_run=args.dry_run)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("=== Full sync finished in %.1f s ===", elapsed)


if __name__ == "__main__":
    main()
