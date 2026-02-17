"""
Scrapy pipelines for processing and loading campground items.
"""
import sys
import logging
from pathlib import Path
from scrapy.exceptions import DropItem

# Add backend root to path so we can import our modules
_backend_root = str(Path(__file__).resolve().parent.parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Validates items have required fields before processing."""

    REQUIRED_FIELDS = ["name", "source", "source_id"]

    def process_item(self, item, spider):
        for field in self.REQUIRED_FIELDS:
            if not item.get(field):
                raise DropItem(
                    f"Missing required field '{field}' in item from {spider.name}"
                )

        # Ensure state is uppercase 2-letter code
        state = item.get("state", "")
        if state and len(state) > 2:
            from config.regions import normalize_state
            item["state"] = normalize_state(state)

        return item


class FirestorePipeline:
    """Normalizes items and writes to Firestore in batches."""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.buffer = []
        self.batch_size = 500
        self.stats = {"processed": 0, "loaded": 0, "errors": 0}
        self.loader = None

    @classmethod
    def from_crawler(cls, crawler):
        dry_run = crawler.settings.getbool("DRY_RUN", False)
        return cls(dry_run=dry_run)

    def open_spider(self, spider):
        if not self.dry_run:
            from loaders.firestore_loader import FirestoreLoader
            self.loader = FirestoreLoader()
        logger.info(
            "FirestorePipeline opened for %s (dry_run=%s)",
            spider.name, self.dry_run,
        )

    def process_item(self, item, spider):
        from transforms.normalizer import normalize_scraped

        try:
            normalized = normalize_scraped(dict(item), spider.source_name)
            self.buffer.append(normalized)
            self.stats["processed"] += 1

            if len(self.buffer) >= self.batch_size:
                self._flush_buffer(spider)
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(
                "Failed to normalize item from %s: %s", spider.name, e
            )

        return item

    def close_spider(self, spider):
        if self.buffer:
            self._flush_buffer(spider)

        logger.info(
            "FirestorePipeline closed for %s: %s", spider.name, self.stats
        )

    def _flush_buffer(self, spider):
        if self.dry_run:
            logger.info(
                "[DRY RUN] Would load %d records from %s",
                len(self.buffer), spider.name,
            )
            self.stats["loaded"] += len(self.buffer)
        elif self.loader:
            try:
                result = self.loader.upsert_batch(self.buffer)
                loaded = result.get("created", 0) + result.get("updated", 0)
                self.stats["loaded"] += loaded
                logger.info(
                    "Flushed %d records from %s: %s",
                    len(self.buffer), spider.name, result,
                )
            except Exception as e:
                self.stats["errors"] += len(self.buffer)
                logger.error("Batch flush failed for %s: %s", spider.name, e)

        self.buffer = []
