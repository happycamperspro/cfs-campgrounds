"""
Custom Scrapy middlewares for campground scrapers.
"""
import logging
from scrapy import signals
from scrapy.exceptions import IgnoreRequest

logger = logging.getLogger(__name__)


class CampgroundScrapersMiddleware:
    """Custom download middleware with error tracking."""

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(s.spider_closed, signal=signals.spider_closed)
        return s

    def __init__(self):
        self.error_count = 0
        self.request_count = 0

    def process_request(self, request, spider):
        self.request_count += 1
        return None

    def process_response(self, request, response, spider):
        if response.status >= 400:
            self.error_count += 1
            logger.warning(
                "HTTP %d on %s (errors: %d/%d)",
                response.status, request.url,
                self.error_count, self.request_count,
            )
            # Stop spider if error rate exceeds 50% after 10+ requests
            if self.request_count >= 10 and self.error_count / self.request_count > 0.5:
                logger.error(
                    "Error rate too high (%.0f%%), stopping spider",
                    (self.error_count / self.request_count) * 100,
                )
                spider.crawler.engine.close_spider(spider, "high_error_rate")
        return response

    def process_exception(self, request, exception, spider):
        self.error_count += 1
        logger.error("Request exception on %s: %s", request.url, exception)
        return None

    def spider_opened(self, spider):
        logger.info("Spider opened: %s", spider.name)

    def spider_closed(self, spider, reason):
        logger.info(
            "Spider closed: %s (reason: %s, requests: %d, errors: %d)",
            spider.name, reason, self.request_count, self.error_count,
        )
