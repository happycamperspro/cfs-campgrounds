"""
Spider for KOA (Kampgrounds of America) campgrounds.

Crawls koa.com starting from the campground directory, following state and
individual campground links.  ~500 KOA locations in the US.

Respects robots.txt and uses conservative request rates.
"""

import json
import logging
import re

import scrapy
from campground_scrapers.items import CampgroundItem

logger = logging.getLogger(__name__)


class KOASpider(scrapy.Spider):
    name = "koa"
    source_name = "koa"
    allowed_domains = ["koa.com"]
    start_urls = ["https://koa.com/campgrounds/"]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DEPTH_LIMIT": 4,
    }

    # US state abbreviations for filtering directory links
    US_STATES = {
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
        "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
        "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
        "maine", "maryland", "massachusetts", "michigan", "minnesota",
        "mississippi", "missouri", "montana", "nebraska", "nevada",
        "new-hampshire", "new-jersey", "new-mexico", "new-york",
        "north-carolina", "north-dakota", "ohio", "oklahoma", "oregon",
        "pennsylvania", "rhode-island", "south-carolina", "south-dakota",
        "tennessee", "texas", "utah", "vermont", "virginia", "washington",
        "west-virginia", "wisconsin", "wyoming",
    }

    def parse(self, response):
        """Parse the top-level campground directory to find state pages."""
        # KOA directory lists states as links like /campgrounds/california/
        state_links = response.css('a[href*="/campgrounds/"]::attr(href)').getall()
        for href in state_links:
            # Only follow links that look like state directories
            slug = href.strip("/").split("/")[-1] if href else ""
            if slug.lower() in self.US_STATES:
                yield response.follow(href, callback=self.parse_state)

        # Also try to find state links from a structured listing or map
        for link in response.css("a.state-link::attr(href), "
                                 "a[data-state]::attr(href), "
                                 "ul.state-list a::attr(href)").getall():
            yield response.follow(link, callback=self.parse_state)

    def parse_state(self, response):
        """Parse a state page to find individual campground links."""
        # KOA state pages list campgrounds with links to detail pages
        campground_links = response.css(
            'a[href*="/campgrounds/"][href$="/"]::attr(href)'
        ).getall()

        for href in campground_links:
            # Campground detail URLs typically have a city-specific slug
            # e.g., /campgrounds/california/san-diego-koa/
            parts = href.strip("/").split("/")
            if len(parts) >= 3 and parts[0] == "campgrounds":
                yield response.follow(href, callback=self.parse_campground)

        # Also look for card-style listings
        for card in response.css("a.campground-card::attr(href), "
                                 "div.campground-listing a::attr(href), "
                                 "a[data-campground-id]::attr(href)").getall():
            yield response.follow(card, callback=self.parse_campground)

        # Handle pagination
        next_page = response.css(
            'a.next::attr(href), '
            'a[rel="next"]::attr(href), '
            'a.pagination-next::attr(href)'
        ).get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_state)

    def parse_campground(self, response):
        """Parse an individual KOA campground detail page."""
        item = CampgroundItem()
        item["source"] = self.source_name

        # --- Source ID from URL ---
        item["source_id"] = self._extract_source_id(response.url)

        # --- Try JSON-LD first (most reliable) ---
        json_ld = self._extract_json_ld(response)
        if json_ld:
            item["name"] = json_ld.get("name", "")
            address = json_ld.get("address", {})
            if isinstance(address, dict):
                item["address"] = address.get("streetAddress", "")
                item["city"] = address.get("addressLocality", "")
                item["state"] = address.get("addressRegion", "")
                item["zip_code"] = address.get("postalCode", "")
            geo = json_ld.get("geo", {})
            if isinstance(geo, dict):
                item["latitude"] = self._to_float(geo.get("latitude"))
                item["longitude"] = self._to_float(geo.get("longitude"))
            item["phone"] = json_ld.get("telephone", "")
            item["website"] = json_ld.get("url", response.url)
            item["description"] = json_ld.get("description", "")
            rating = json_ld.get("aggregateRating", {})
            if isinstance(rating, dict):
                item["source_rating"] = self._to_float(rating.get("ratingValue"))
                item["source_review_count"] = self._to_int(rating.get("reviewCount"))
            photos = json_ld.get("image", [])
            if isinstance(photos, list):
                item["photos"] = [{"url": p, "caption": ""} for p in photos if isinstance(p, str)]
            elif isinstance(photos, str):
                item["photos"] = [{"url": photos, "caption": ""}]

        # --- Fall back to / supplement with CSS selectors ---
        if not item.get("name"):
            item["name"] = (
                response.css("h1.campground-name::text").get("").strip()
                or response.css("h1::text").get("").strip()
            )
        if not item.get("description"):
            item["description"] = (
                response.css("div.campground-description p::text").get("").strip()
                or response.css('meta[name="description"]::attr(content)').get("")
            )
        if not item.get("phone"):
            item["phone"] = (
                response.css('a[href^="tel:"]::text').get("").strip()
                or response.css("span.phone::text").get("").strip()
            )

        # --- Address fallback ---
        if not item.get("address"):
            item["address"] = response.css(
                "span.street-address::text, "
                "div.address-line::text"
            ).get("").strip()
        if not item.get("city"):
            item["city"] = response.css(
                "span.locality::text, span.city::text"
            ).get("").strip()
        if not item.get("state"):
            item["state"] = response.css(
                "span.region::text, span.state::text"
            ).get("").strip()
        if not item.get("zip_code"):
            item["zip_code"] = response.css(
                "span.postal-code::text, span.zip::text"
            ).get("").strip()

        # --- Coordinates fallback from embedded map data ---
        if not item.get("latitude") or not item.get("longitude"):
            lat, lng = self._extract_coords_from_page(response)
            if lat is not None:
                item["latitude"] = lat
                item["longitude"] = lng

        # --- Reservation URL ---
        item["reservation_url"] = (
            response.css('a[href*="reserve"]::attr(href)').get("")
            or response.css('a.book-now::attr(href)').get("")
            or response.css('a[data-action="reserve"]::attr(href)').get("")
        )
        if not item.get("website"):
            item["website"] = response.url

        # --- Pricing ---
        price_texts = response.css(
            "span.price::text, div.pricing span::text, "
            "span.rate-amount::text"
        ).getall()
        prices = self._extract_prices(price_texts)
        if prices:
            item["price_min"] = min(prices)
            item["price_max"] = max(prices)

        # --- Site types ---
        site_type_elements = response.css(
            "div.site-types li::text, "
            "ul.accommodation-types li::text, "
            "div.site-type-name::text"
        ).getall()
        item["site_types"] = self._classify_site_types(site_type_elements)

        # --- Amenities ---
        amenity_texts = response.css(
            "ul.amenities li::text, "
            "div.amenity-item::text, "
            "div.amenity-name::text, "
            "span.amenity::text"
        ).getall()
        amenities = [a.strip().lower() for a in amenity_texts if a.strip()]
        item["hookups"] = self._extract_hookups(amenities)
        item["facilities"] = self._extract_facilities(amenities)
        item["activities"] = self._extract_activities(amenities)

        # --- Pets ---
        page_text = response.text.lower()
        if "pet friendly" in page_text or "pets welcome" in page_text or "dog park" in page_text:
            item["pets_allowed"] = True
        elif "no pets" in page_text:
            item["pets_allowed"] = False

        # --- Photos fallback ---
        if not item.get("photos"):
            photo_urls = response.css(
                "div.gallery img::attr(src), "
                "div.photo-gallery img::attr(data-src), "
                "img.campground-photo::attr(src)"
            ).getall()
            item["photos"] = [
                {"url": response.urljoin(url), "caption": ""}
                for url in photo_urls[:20]
                if url
            ]

        # --- KOA type as managed_by ---
        koa_type = response.css(
            "span.koa-type::text, div.campground-type::text"
        ).get("").strip()
        item["managed_by"] = f"KOA - {koa_type}" if koa_type else "KOA"

        # --- Season ---
        season_text = response.css(
            "span.season::text, div.open-dates::text"
        ).get("").strip()
        if season_text:
            item["season"] = season_text

        # --- Total sites ---
        sites_text = response.css(
            "span.total-sites::text, div.site-count::text"
        ).get("").strip()
        if sites_text:
            item["total_sites"] = self._to_int(sites_text)

        item["reservation_type"] = "reservable"

        # Only yield if we have at least a name
        if item.get("name"):
            yield item
        else:
            logger.warning("Skipping campground with no name: %s", response.url)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _extract_source_id(self, url):
        """Derive a stable source ID from the URL path."""
        path = url.rstrip("/").split("/")
        # e.g., /campgrounds/california/san-diego-koa/ -> california-san-diego-koa
        relevant = [p for p in path if p and p != "campgrounds"]
        return "-".join(relevant[-2:]) if len(relevant) >= 2 else relevant[-1] if relevant else url

    def _extract_json_ld(self, response):
        """Extract the first Campground/LodgingBusiness JSON-LD block."""
        scripts = response.css('script[type="application/ld+json"]::text').getall()
        for raw in scripts:
            try:
                data = json.loads(raw)
                # Handle arrays of JSON-LD objects
                if isinstance(data, list):
                    for obj in data:
                        if self._is_campground_schema(obj):
                            return obj
                elif self._is_campground_schema(data):
                    return data
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    @staticmethod
    def _is_campground_schema(obj):
        """Check if a JSON-LD object describes a campground."""
        if not isinstance(obj, dict):
            return False
        schema_type = obj.get("@type", "")
        if isinstance(schema_type, list):
            types = [t.lower() for t in schema_type]
        else:
            types = [schema_type.lower()]
        campground_types = {
            "campground", "lodgingbusiness", "rvpark",
            "touristattraction", "localbusiness", "park",
        }
        return bool(campground_types & set(types))

    def _extract_coords_from_page(self, response):
        """Try to pull lat/lng from embedded JavaScript or data attributes."""
        # Look for data attributes on map elements
        lat = response.css('[data-lat]::attr(data-lat)').get()
        lng = response.css(
            '[data-lng]::attr(data-lng), [data-lon]::attr(data-lon)'
        ).get()
        if lat and lng:
            return self._to_float(lat), self._to_float(lng)

        # Look for lat/lng in inline scripts
        body = response.text
        lat_match = re.search(r'["\']?(?:lat(?:itude)?)["\']?\s*[:=]\s*(-?\d+\.\d+)', body)
        lng_match = re.search(r'["\']?(?:lng|lon(?:gitude)?)["\']?\s*[:=]\s*(-?\d+\.\d+)', body)
        if lat_match and lng_match:
            return float(lat_match.group(1)), float(lng_match.group(1))

        return None, None

    @staticmethod
    def _extract_prices(texts):
        """Pull dollar amounts from a list of text strings."""
        prices = []
        for t in texts:
            for match in re.findall(r'\$\s*(\d+(?:\.\d{1,2})?)', t):
                val = float(match)
                if 0 < val < 1000:  # sanity check
                    prices.append(val)
        return prices

    @staticmethod
    def _classify_site_types(texts):
        """Map raw site-type labels to canonical types."""
        mapping = {
            "tent": "tent", "rv": "rv", "cabin": "cabin",
            "lodge": "cabin", "deluxe cabin": "cabin",
            "travel trailer": "rv", "pull-thru": "rv",
            "back-in": "rv", "glamping": "glamping",
        }
        types = set()
        for t in texts:
            key = t.strip().lower()
            for keyword, canonical in mapping.items():
                if keyword in key:
                    types.add(canonical)
        return sorted(types) if types else []

    @staticmethod
    def _extract_hookups(amenities):
        hookup_keywords = {
            "electric": "electric", "30 amp": "electric", "50 amp": "electric",
            "water hookup": "water", "water hook": "water",
            "sewer": "sewer", "full hookup": "sewer",
        }
        found = set()
        for a in amenities:
            for keyword, hookup in hookup_keywords.items():
                if keyword in a:
                    found.add(hookup)
        if "full hookup" in " ".join(amenities):
            found.update(["electric", "water", "sewer"])
        return sorted(found)

    @staticmethod
    def _extract_facilities(amenities):
        facility_keywords = [
            "restroom", "shower", "laundry", "pool", "wifi", "wi-fi",
            "store", "dump station", "playground", "clubhouse",
            "hot tub", "game room",
        ]
        return sorted({kw for kw in facility_keywords if any(kw in a for a in amenities)})

    @staticmethod
    def _extract_activities(amenities):
        activity_keywords = [
            "hiking", "fishing", "swimming", "biking", "kayaking",
            "canoeing", "horseback", "golf", "mini golf", "boating",
        ]
        return sorted({kw for kw in activity_keywords if any(kw in a for a in amenities)})

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
