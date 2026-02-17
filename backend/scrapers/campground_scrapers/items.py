"""
Scrapy item definitions for campground data.
All spiders yield CampgroundItem instances.
"""
import scrapy


class CampgroundItem(scrapy.Item):
    """Unified campground item yielded by all spiders."""
    # Identity
    name = scrapy.Field()
    source = scrapy.Field()
    source_id = scrapy.Field()

    # Location
    address = scrapy.Field()
    city = scrapy.Field()
    state = scrapy.Field()
    zip_code = scrapy.Field()
    latitude = scrapy.Field()
    longitude = scrapy.Field()

    # Contact
    phone = scrapy.Field()
    email = scrapy.Field()
    website = scrapy.Field()
    reservation_url = scrapy.Field()

    # Details
    description = scrapy.Field()
    total_sites = scrapy.Field()
    site_types = scrapy.Field()       # list of strings: ["tent", "rv", "cabin"]
    max_rv_length = scrapy.Field()
    elevation = scrapy.Field()
    season = scrapy.Field()
    reservation_type = scrapy.Field()  # "reservable" | "first-come" | "mixed"
    price_min = scrapy.Field()
    price_max = scrapy.Field()
    managed_by = scrapy.Field()
    park_name = scrapy.Field()

    # Amenities
    hookups = scrapy.Field()          # list: ["electric", "water", "sewer"]
    facilities = scrapy.Field()       # list: ["restrooms", "showers", "laundry"]
    activities = scrapy.Field()       # list: ["hiking", "fishing", "swimming"]
    pets_allowed = scrapy.Field()     # bool
    accessibility = scrapy.Field()    # bool
    cell_service = scrapy.Field()     # "none" | "weak" | "moderate" | "strong"

    # Media
    photos = scrapy.Field()           # list of {"url": str, "caption": str}

    # Ratings from source
    source_rating = scrapy.Field()
    source_review_count = scrapy.Field()
