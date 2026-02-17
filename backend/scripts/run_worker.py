#!/usr/bin/env python3
"""
Background worker that polls Firestore for pending scraper runs.

The admin dashboard writes documents to the ``_scraper_runs`` collection
with ``status="pending"``.  This worker picks them up, executes the
requested spider, and writes stats back to the run document.

CLI
---
    python run_worker.py [--poll-interval 30] [--daemon]

Graceful shutdown on SIGINT / SIGTERM.
"""

import sys
from pathlib import Path

_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

import argparse
import logging
import os
import signal
import time
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, firestore

from config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("run_worker")

SCRAPER_RUNS_COLLECTION = "_scraper_runs"
AVAILABLE_SPIDERS = ["koa", "hipcamp", "good_sam", "thousand_trails", "state_parks"]

# ------------------------------------------------------------------
# Graceful shutdown
# ------------------------------------------------------------------

_shutdown_requested = False


def _handle_signal(signum, _frame):
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info("Received %s -- requesting graceful shutdown ...", sig_name)
    _shutdown_requested = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ------------------------------------------------------------------
# Firebase bootstrap
# ------------------------------------------------------------------

def _init_firebase():
    """Initialise Firebase Admin SDK (idempotent)."""
    if firebase_admin._apps:
        return
    sa_path = settings.FIREBASE_SERVICE_ACCOUNT_PATH
    if sa_path:
        cred = credentials.Certificate(sa_path)
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()


# ------------------------------------------------------------------
# Spider execution
# ------------------------------------------------------------------

def _run_spider(spider_name: str, spider_kwargs: dict) -> dict:
    """Run a Scrapy spider in-process and return basic stats.

    Returns a dict with ``items_scraped``, ``errors``, ``status``,
    and ``finished_at``.
    """
    # Ensure scrapers package is importable
    scrapers_dir = Path(_backend_root) / "scrapers"
    if str(scrapers_dir) not in sys.path:
        sys.path.insert(0, str(scrapers_dir))

    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    scrapy_settings = get_project_settings()

    # Apply optional limit
    limit = spider_kwargs.pop("limit", None)
    if limit:
        scrapy_settings.set("CLOSESPIDER_ITEMCOUNT", int(limit))

    # Apply optional dry_run
    dry_run = spider_kwargs.pop("dry_run", False)
    if dry_run:
        scrapy_settings.set("DRY_RUN", True)

    process = CrawlerProcess(scrapy_settings)

    spider_loader = process.spider_loader
    available = spider_loader.list()
    if spider_name not in available:
        return {
            "items_scraped": 0,
            "errors": 1,
            "status": "failed",
            "error_message": f"Spider '{spider_name}' not found. Available: {available}",
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }

    spider_cls = spider_loader.load(spider_name)
    process.crawl(spider_cls, **spider_kwargs)
    process.start(install_signal_handlers=False)

    # Aggregate stats from the crawler(s)
    items_scraped = 0
    error_count = 0
    for crawler in process.crawlers:
        stats = crawler.stats.get_stats()
        items_scraped += stats.get("item_scraped_count", 0)
        error_count += stats.get("log_count/ERROR", 0)

    return {
        "items_scraped": items_scraped,
        "errors": error_count,
        "status": "completed" if error_count == 0 else "completed_with_errors",
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


# ------------------------------------------------------------------
# Polling loop
# ------------------------------------------------------------------

def _poll_once(db) -> bool:
    """Check for a pending run document and execute it.

    Returns ``True`` if a run was processed, ``False`` otherwise.
    """
    collection_ref = db.collection(SCRAPER_RUNS_COLLECTION)
    query = (
        collection_ref
        .where("status", "==", "pending")
        .order_by("created_at")
        .limit(1)
    )
    docs = list(query.stream())

    if not docs:
        return False

    doc = docs[0]
    run_data = doc.to_dict()
    run_id = doc.id
    spider_name = run_data.get("spider_name", "")

    logger.info(
        "Found pending run %s for spider '%s'.",
        run_id,
        spider_name,
    )

    # Validate spider name
    if spider_name not in AVAILABLE_SPIDERS:
        logger.error("Unknown spider '%s' in run %s.", spider_name, run_id)
        doc.reference.update({
            "status": "failed",
            "error_message": f"Unknown spider: {spider_name}",
            "finished_at": datetime.now(timezone.utc),
        })
        return True

    # Mark as running
    doc.reference.update({
        "status": "running",
        "started_at": datetime.now(timezone.utc),
    })

    # Build spider kwargs from the run document
    spider_kwargs = {}
    if run_data.get("states"):
        spider_kwargs["states"] = run_data["states"]
    if run_data.get("limit"):
        spider_kwargs["limit"] = run_data["limit"]
    if run_data.get("dry_run"):
        spider_kwargs["dry_run"] = True

    # Execute
    logger.info("Executing spider '%s' (run %s) ...", spider_name, run_id)
    try:
        result = _run_spider(spider_name, spider_kwargs)
        doc.reference.update({
            "status": result["status"],
            "items_scraped": result.get("items_scraped", 0),
            "errors": result.get("errors", 0),
            "error_message": result.get("error_message", ""),
            "finished_at": datetime.now(timezone.utc),
        })
        logger.info(
            "Run %s finished: %s (items=%d, errors=%d).",
            run_id,
            result["status"],
            result.get("items_scraped", 0),
            result.get("errors", 0),
        )
    except Exception as exc:
        logger.exception("Run %s failed with exception.", run_id)
        doc.reference.update({
            "status": "failed",
            "error_message": str(exc),
            "finished_at": datetime.now(timezone.utc),
        })

    return True


def _worker_loop(poll_interval: int) -> None:
    """Main polling loop.  Runs until a shutdown signal is received."""
    _init_firebase()
    db = firestore.client()

    logger.info(
        "Worker started.  Polling '%s' every %d s.  PID=%d",
        SCRAPER_RUNS_COLLECTION,
        poll_interval,
        os.getpid(),
    )

    while not _shutdown_requested:
        try:
            processed = _poll_once(db)
            if processed:
                # Immediately check for more pending runs
                continue
        except Exception:
            logger.exception("Error during poll cycle.")

        # Sleep in small increments so we can react to shutdown signals promptly
        for _ in range(poll_interval):
            if _shutdown_requested:
                break
            time.sleep(1)

    logger.info("Worker shutting down gracefully.")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Background worker that polls Firestore for pending scraper runs.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Seconds between Firestore polls (default: 30).",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        default=False,
        help="Fork into the background as a daemon process.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    if args.daemon:
        pid = os.fork()
        if pid > 0:
            # Parent process -- print child PID and exit
            print(f"Worker daemonised.  PID={pid}")
            sys.exit(0)
        # Child process -- detach from terminal
        os.setsid()
        # Redirect stdio to /dev/null
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)

    _worker_loop(poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
