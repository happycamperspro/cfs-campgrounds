"""
Scrapy settings for campground_scrapers project.
"""

BOT_NAME = "campground_scrapers"
SPIDER_MODULES = ["campground_scrapers.spiders"]
NEWSPIDER_MODULE = "campground_scrapers.spiders"

# Obey robots.txt
ROBOTSTXT_OBEY = True

# Conservative concurrency
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# Respectful crawling delay
DOWNLOAD_DELAY = 2

# Auto-throttle
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# User agent rotation
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy_fake_useragent.middleware.RandomUserAgentMiddleware": 400,
    "campground_scrapers.middlewares.CampgroundScrapersMiddleware": 543,
}

FAKEUSERAGENT_PROVIDERS = [
    "scrapy_fake_useragent.providers.FakeUserAgentProvider",
    "scrapy_fake_useragent.providers.FakerProvider",
]

# Item pipelines
ITEM_PIPELINES = {
    "campground_scrapers.pipelines.ValidationPipeline": 100,
    "campground_scrapers.pipelines.FirestorePipeline": 300,
}

# Logging
LOG_LEVEL = "INFO"

# Retry settings
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Request timeout
DOWNLOAD_TIMEOUT = 30

# Respect crawl depth
DEPTH_LIMIT = 5

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
