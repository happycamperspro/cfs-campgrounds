"""
Spider for Hipcamp campground listings.

Hipcamp is a React SPA, so direct HTML scraping of listing pages yields little
content.  This spider uses a sitemap-based strategy to discover listing URLs and
then extracts data from JSON-LD, Open Graph meta tags, and any inline
__NEXT_DATA__ / hydration JSON that the server-side render provides.

Respects robots.txt and uses conservative request rates.
"""

import json
import logging
import re

import scrapy
from scrapy.spiders import SitemapSpider
from campground_scrapers.items import CampgroundItem

logger = logging.getLogger(__name__)


class HipcampSpider(SitemapSpider):
    name = "hipcamp"
    source_name = "hipcamp"
    allowed_domains = ["hipcamp.com"]

    # Sitemap-based discovery -- Hipcamp exposes sitemaps for listing pages
    sitemap_urls = [
        "https://www.hipcamp.com/sitemap.xml",
    ]
    # Only follow listing URLs (e.g. /land/california/some-campground)
    sitemap_rules = [
        (r"/land/[a-z\-]+/[a-z0-9\-]+", "parse_campground"),
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DEPTH_LIMIT": 2,
        "ROBOTSTXT_OBEY": True,
    }

    # ------------------------------------------------------------------
    # Fallback: if sitemap discovery is insufficient, seed from the
    # explore page to gather region links.
    # ------------------------------------------------------------------
    def start_requests(self):
        """Yield sitemap requests first, then fall back to explore page."""
        # Let SitemapSpider handle sitemap requests
        yield from super().start_requests()
        # Also seed from the explore page for additional coverage
        yield scrapy.Request(
            "https://www.hipcamp.com/explore",
            callback=self.parse_explore,
            priority=-1,  # lower priority than sitemap
        )

    def parse_explore(self, response):
        """Follow region/state links from the explore page."""
        links = response.css(
            'a[href*="/land/"]::attr(href), '
            'a[href*="/discover/"]::attr(href)'
        ).getall()
        seen = set()
        for href in links:
            full = response.urljoin(href)
            if full not in seen:
                seen.add(full)
                # Region listing pages
                if "/discover/" in href or href.count("/") <= 4:
                    yield response.follow(href, callback=self.parse_listing_page)
                else:
                    yield response.follow(href, callback=self.parse_campground)

    def parse_listing_page(self, response):
        """Parse a region/category listing page for individual campground links."""
        links = response.css('a[href*="/land/"]::attr(href)').getall()
        for href in links:
            # Only follow links that look like individual listings
            parts = href.strip("/").split("/")
            if len(parts) >= 3 and parts[0] == "land":
                yield response.follow(href, callback=self.parse_campground)

        # Pagination
        next_page = response.css(
            'a[rel="next"]::attr(href), '
            'button[aria-label="Next"] a::attr(href)'
        ).get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_listing_page)

    def parse_campground(self, response):
        """Parse an individual Hipcamp listing page."""
        item = CampgroundItem()
        item["source"] = self.source_name
        item["source_id"] = self._extract_source_id(response.url)
        item["website"] = response.url
        item["reservation_url"] = response.url  # Hipcamp listings are bookable

        # ---- Strategy 1: __NEXT_DATA__ (Next.js hydration payload) ----
        next_data = self._extract_next_data(response)
        if next_data:
            self._populate_from_next_data(item, next_data)

        # ---- Strategy 2: JSON-LD structured data ----
        json_ld = self._extract_json_ld(response)
        if json_ld:
            self._populate_from_json_ld(item, json_ld)

        # ---- Strategy 3: Open Graph / meta tags ----
        self._populate_from_meta(item, response)

        # ---- Strategy 4: CSS / visible HTML (limited for SPA) ----
        self._populate_from_html(item, response)

        # Only yield if we have at least a name
        if item.get("name"):
            yield item
        else:
            logger.warning("Skipping listing with no name: %s", response.url)

    # ------------------------------------------------------------------
    # __NEXT_DATA__ extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_next_data(response):
        """Parse the __NEXT_DATA__ JSON blob injected by Next.js SSR."""
        script = response.css('script#__NEXT_DATA__::text').get()
        if not script:
            return None
        try:
            data = json.loads(script)
            return data.get("props", {}).get("pageProps", {})
        except (json.JSONDecodeError, TypeError):
            return None

    def _populate_from_next_data(self, item, page_props):
        """Fill item fields from the Next.js page props."""
        # Hipcamp typically nests the listing under a key like "listing" or "property"
        listing = (
            page_props.get("listing")
            or page_props.get("property")
            or page_props.get("campground")
            or page_props
        )
        if not isinstance(listing, dict):
            return

        if not item.get("name"):
            item["name"] = listing.get("name", "")
        if not item.get("description"):
            item["description"] = listing.get("description", "")

        # Location
        location = listing.get("location", {}) or {}
        if not item.get("city"):
            item["city"] = location.get("city", "")
        if not item.get("state"):
            item["state"] = location.get("state", "") or location.get("region", "")
        if not item.get("address"):
            item["address"] = location.get("address", "")
        if not item.get("zip_code"):
            item["zip_code"] = location.get("zipCode", "") or location.get("zip", "")
        if not item.get("latitude"):
            item["latitude"] = self._to_float(
                location.get("lat") or listing.get("latitude")
            )
        if not item.get("longitude"):
            item["longitude"] = self._to_float(
                location.get("lng") or location.get("lon") or listing.get("longitude")
            )

        # Pricing
        price = listing.get("price") or listing.get("pricePerNight") or {}
        if isinstance(price, dict):
            item["price_min"] = self._to_float(price.get("min") or price.get("amount"))
            item["price_max"] = self._to_float(price.get("max"))
        elif isinstance(price, (int, float)):
            item["price_min"] = float(price)

        # Rating
        if not item.get("source_rating"):
            item["source_rating"] = self._to_float(listing.get("rating"))
        if not item.get("source_review_count"):
            item["source_review_count"] = self._to_int(listing.get("reviewCount"))

        # Photos
        images = listing.get("images") or listing.get("photos") or []
        if images and not item.get("photos"):
            item["photos"] = [
                {
                    "url": img.get("url", "") if isinstance(img, dict) else str(img),
                    "caption": img.get("caption", "") if isinstance(img, dict) else "",
                }
                for img in images[:20]
            ]

        # Amenities / features
        amenities = listing.get("amenities") or listing.get("features") or []
        if isinstance(amenities, list):
            lowered = [str(a).lower() for a in amenities]
            item["hookups"] = self._extract_hookups(lowered)
            item["facilities"] = self._extract_facilities(lowered)
            item["activities"] = self._extract_activities(lowered)

        # Pets
        pets = listing.get("petsAllowed") or listing.get("pets")
        if pets is not None:
            item["pets_allowed"] = bool(pets)

        # Site types
        site_types = listing.get("siteTypes") or listing.get("accommodationTypes") or []
        if isinstance(site_types, list):
            item["site_types"] = self._classify_site_types(site_types)

        # Managed by / host
        host = listing.get("host") or listing.get("owner") or {}
        if isinstance(host, dict) and host.get("name"):
            item["managed_by"] = host["name"]

    # ------------------------------------------------------------------
    # JSON-LD extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json_ld(response):
        """Extract the first relevant JSON-LD block."""
        for raw in response.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict) and obj.get("@type"):
                            return obj
                elif isinstance(data, dict) and data.get("@type"):
                    return data
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    def _populate_from_json_ld(self, item, ld):
        """Fill item fields from JSON-LD."""
        if not item.get("name"):
            item["name"] = ld.get("name", "")
        if not item.get("description"):
            item["description"] = ld.get("description", "")

        address = ld.get("address", {})
        if isinstance(address, dict):
            if not item.get("address"):
                item["address"] = address.get("streetAddress", "")
            if not item.get("city"):
                item["city"] = address.get("addressLocality", "")
            if not item.get("state"):
                item["state"] = address.get("addressRegion", "")
            if not item.get("zip_code"):
                item["zip_code"] = address.get("postalCode", "")

        geo = ld.get("geo", {})
        if isinstance(geo, dict):
            if not item.get("latitude"):
                item["latitude"] = self._to_float(geo.get("latitude"))
            if not item.get("longitude"):
                item["longitude"] = self._to_float(geo.get("longitude"))

        rating = ld.get("aggregateRating", {})
        if isinstance(rating, dict):
            if not item.get("source_rating"):
                item["source_rating"] = self._to_float(rating.get("ratingValue"))
            if not item.get("source_review_count"):
                item["source_review_count"] = self._to_int(rating.get("reviewCount"))

        images = ld.get("image", [])
        if images and not item.get("photos"):
            if isinstance(images, str):
                images = [images]
            item["photos"] = [
                {"url": url, "caption": ""} for url in images[:20] if isinstance(url, str)
            ]

    # ------------------------------------------------------------------
    # Meta tag extraction (Open Graph, standard meta)
    # ------------------------------------------------------------------

    @staticmethod
    def _populate_from_meta(item, response):
        """Fill item fields from Open Graph and standard meta tags."""
        if not item.get("name"):
            item["name"] = (
                response.css('meta[property="og:title"]::attr(content)').get("")
                or response.css("title::text").get("")
            ).strip()
        if not item.get("description"):
            item["description"] = (
                response.css('meta[property="og:description"]::attr(content)').get("")
                or response.css('meta[name="description"]::attr(content)').get("")
            ).strip()
        if not item.get("photos"):
            og_image = response.css('meta[property="og:image"]::attr(content)').get("")
            if og_image:
                item["photos"] = [{"url": og_image, "caption": ""}]

        # Hipcamp sometimes encodes lat/lng in meta
        lat = response.css('meta[property="place:location:latitude"]::attr(content)').get()
        lng = response.css('meta[property="place:location:longitude"]::attr(content)').get()
        if lat and lng and not item.get("latitude"):
            try:
                item["latitude"] = float(lat)
                item["longitude"] = float(lng)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # HTML fallback extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _populate_from_html(item, response):
        """Best-effort extraction from rendered HTML (limited for SPA)."""
        if not item.get("name"):
            item["name"] = (
                response.css("h1::text").get("")
                or response.css('[data-testid="listing-title"]::text').get("")
            ).strip()

        if not item.get("phone"):
            item["phone"] = response.css('a[href^="tel:"]::text').get("").strip()

        if not item.get("email"):
            item["email"] = response.css('a[href^="mailto:"]::text').get("").strip()

        # Price from visible text
        if not item.get("price_min"):
            price_text = response.css(
                'span[data-testid="price"]::text, '
                'div.price::text, '
                'span.nightly-price::text'
            ).get("")
            match = re.search(r'\$\s*(\d+)', price_text)
            if match:
                item["price_min"] = float(match.group(1))

    # ------------------------------------------------------------------
    # Amenity classification helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_hookups(amenities):
        keywords = {
            "electric": "electric", "electricity": "electric",
            "water hookup": "water", "water hook-up": "water",
            "sewer": "sewer", "full hookup": "sewer",
        }
        found = set()
        for a in amenities:
            for kw, hookup in keywords.items():
                if kw in a:
                    found.add(hookup)
        if any("full hookup" in a for a in amenities):
            found.update(["electric", "water", "sewer"])
        return sorted(found)

    @staticmethod
    def _extract_facilities(amenities):
        keywords = [
            "restroom", "shower", "laundry", "pool", "wifi", "wi-fi",
            "store", "dump station", "playground", "hot tub", "fire pit",
            "picnic table", "drinking water", "trash",
        ]
        return sorted({kw for kw in keywords if any(kw in a for a in amenities)})

    @staticmethod
    def _extract_activities(amenities):
        keywords = [
            "hiking", "fishing", "swimming", "biking", "kayaking",
            "canoeing", "horseback", "surfing", "climbing", "stargazing",
            "wildlife viewing", "paddleboarding",
        ]
        return sorted({kw for kw in keywords if any(kw in a for a in amenities)})

    @staticmethod
    def _classify_site_types(raw_types):
        mapping = {
            "tent": "tent", "camping": "tent", "rv": "rv",
            "cabin": "cabin", "treehouse": "cabin", "yurt": "yurt",
            "glamping": "glamping", "tipi": "glamping", "tepee": "glamping",
        }
        types = set()
        for t in raw_types:
            key = str(t).strip().lower()
            for keyword, canonical in mapping.items():
                if keyword in key:
                    types.add(canonical)
        return sorted(types) if types else []

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_source_id(url):
        """Derive a stable source ID from the URL path."""
        parts = [p for p in url.rstrip("/").split("/") if p]
        # e.g., hipcamp.com/land/california/cool-campground -> california-cool-campground
        if "land" in parts:
            idx = parts.index("land")
            relevant = parts[idx + 1:]
            return "-".join(relevant) if relevant else url
        return parts[-1] if parts else url

    @staticmethod
    def _to_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(val):
        try:
            return int(re.sub(r"[^\d]", "", str(val)))
        except (TypeError, ValueError):
            return None
