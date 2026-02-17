#!/usr/bin/env python3
"""
Run a single Scrapy spider by name.

CLI
---
    python run_scraper.py SPIDER_NAME [--limit N] [--dry-run] [--states CA,CO,TX]

Available spiders: koa, hipcamp, good_sam, thousand_trails, state_parks

Examples
--------
    # Run the KOA spider with a 20-item cap
    python run_scraper.py koa --limit 20

    # Dry-run the state_parks spider for California and Colorado
    python run_scraper.py state_parks --states CA,CO --dry-run

    # Run the hipcamp spider with no limits
    python run_scraper.py hipcamp
"""

import sys
from pathlib import Path

_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

import argparse
import logging

from config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("run_scraper")

AVAILABLE_SPIDERS = ["koa", "hipcamp", "good_sam", "thousand_trails", "state_parks"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a single Scrapy spider.",
    )
    parser.add_argument(
        "spider",
        choices=AVAILABLE_SPIDERS,
        help="Name of the spider to run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of items scraped (sets CLOSESPIDER_ITEMCOUNT).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Pass DRY_RUN=True to Scrapy settings (no Firestore writes).",
    )
    parser.add_argument(
        "--states",
        type=str,
        default=None,
        help="Comma-separated list of state codes to target (e.g. CA,CO,TX).",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    logger.info("=== run_scraper: %s ===", args.spider)

    # Ensure the scrapers package is importable
    scrapers_dir = Path(_backend_root) / "scrapers"
    if str(scrapers_dir) not in sys.path:
        sys.path.insert(0, str(scrapers_dir))

    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    scrapy_settings = get_project_settings()

    # Pass DRY_RUN through to pipelines
    if args.dry_run:
        scrapy_settings.set("DRY_RUN", True)
        logger.info("  DRY_RUN mode enabled.")

    # Cap items for testing
    if args.limit is not None:
        scrapy_settings.set("CLOSESPIDER_ITEMCOUNT", args.limit)
        logger.info("  Item limit set to %d.", args.limit)

    process = CrawlerProcess(scrapy_settings)

    # Build spider kwargs (passed as constructor arguments)
    spider_kwargs = {}
    if args.states:
        spider_kwargs["states"] = args.states
        logger.info("  Filtering to states: %s", args.states)

    # Resolve the spider class via the loader
    spider_loader = process.spider_loader
    available = spider_loader.list()

    if args.spider not in available:
        logger.error(
            "Spider '%s' not found. Available spiders: %s",
            args.spider,
            available,
        )
        sys.exit(1)

    spider_cls = spider_loader.load(args.spider)
    process.crawl(spider_cls, **spider_kwargs)

    logger.info("Starting crawl ...")
    process.start()
    logger.info("Crawl finished.")


if __name__ == "__main__":
    main()
