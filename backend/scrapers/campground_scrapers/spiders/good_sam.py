"""
Spider for Good Sam campground and RV park listings.

Crawls goodsam.com starting from the campground/RV-park directory, iterating
through all 50 US states and paginating through results.  Good Sam is
particularly strong for RV park data including hookup types, max RV length, and
the Good Sam rating system.

Respects robots.txt and uses conservative request rates.
"""

import json
import logging
import re
from urllib.parse import urlencode, urljoin

import scrapy
from campground_scrapers.items import CampgroundItem

logger = logging.getLogger(__name__)


class GoodSamSpider(scrapy.Spider):
    name = "good_sam"
    source_name = "good_sam"
    allowed_domains = ["goodsam.com"]
    start_urls = ["https://www.goodsam.com/campgrounds-rv-parks/"]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DEPTH_LIMIT": 5,
    }

    # All 50 US states plus DC -- used to seed state-level searches
    US_STATES = [
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
        "connecticut", "delaware", "district-of-columbia", "florida",
        "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
        "kansas", "kentucky", "louisiana", "maine", "maryland",
        "massachusetts", "michigan", "minnesota", "mississippi", "missouri",
        "montana", "nebraska", "nevada", "new-hampshire", "new-jersey",
        "new-mexico", "new-york", "north-carolina", "north-dakota", "ohio",
        "oklahoma", "oregon", "pennsylvania", "rhode-island",
        "south-carolina", "south-dakota", "tennessee", "texas", "utah",
        "vermont", "virginia", "washington", "west-virginia", "wisconsin",
        "wyoming",
    ]

    def parse(self, response):
        """
        Parse the top-level directory.  Two strategies:

        1. Follow state links found on the directory page.
        2. Seed explicit state URLs if the directory doesn't list them.
        """
        # Try to find state links on the page
        state_links = response.css(
            'a[href*="/campgrounds-rv-parks/"]::attr(href)'
        ).getall()

        yielded = set()
        for href in state_links:
            full = response.urljoin(href)
            if full not in yielded:
                yielded.add(full)
                yield response.follow(href, callback=self.parse_state_results)

        # Seed any states we didn't find links for
        for state_slug in self.US_STATES:
            url = f"https://www.goodsam.com/campgrounds-rv-parks/{state_slug}/"
            if url not in yielded:
                yielded.add(url)
                yield scrapy.Request(url, callback=self.parse_state_results)

    def parse_state_results(self, response):
        """Parse a state results page listing campgrounds."""
        # Find individual campground detail links
        detail_links = response.css(
            'a[href*="/campgrounds-rv-parks/"][href$=".html"]::attr(href), '
            'a.campground-name::attr(href), '
            'h2 a::attr(href), '
            'h3 a::attr(href), '
            'div.listing-card a::attr(href), '
            'a.park-name::attr(href)'
        ).getall()

        seen = set()
        for href in detail_links:
            full = response.urljoin(href)
            if full not in seen and full != response.url:
                seen.add(full)
                # Distinguish detail pages from listing pages by depth
                parts = href.strip("/").split("/")
                if len(parts) >= 3:
                    yield response.follow(href, callback=self.parse_campground)
                else:
                    yield response.follow(href, callback=self.parse_state_results)

        # Also try to extract from JSON API responses embedded in the page
        self._follow_api_results(response)

        # Pagination
        next_page = response.css(
            'a.next::attr(href), '
            'a[rel="next"]::attr(href), '
            'li.next a::attr(href), '
            'a[aria-label="Next page"]::attr(href)'
        ).get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_state_results)

        # Numbered pagination (for pages that use ?page=N)
        current_page = response.url
        page_links = response.css('a.page-link::attr(href), ul.pagination a::attr(href)').getall()
        for href in page_links:
            full = response.urljoin(href)
            if full != current_page:
                yield response.follow(href, callback=self.parse_state_results)

    def parse_campground(self, response):
        """Parse an individual Good Sam campground/RV park detail page."""
        item = CampgroundItem()
        item["source"] = self.source_name
        item["source_id"] = self._extract_source_id(response.url)
        item["website"] = response.url

        # --- JSON-LD (highest quality) ---
        json_ld = self._extract_json_ld(response)
        if json_ld:
            self._populate_from_json_ld(item, json_ld)

        # --- HTML extraction ---
        self._populate_from_html(item, response)

        # --- Good Sam rating system ---
        self._extract_good_sam_rating(item, response)

        # --- RV-specific data ---
        self._extract_rv_data(item, response)

        # --- Amenities ---
        self._extract_amenities(item, response)

        # --- Photos ---
        if not item.get("photos"):
            self._extract_photos(item, response)

        # --- Pricing ---
        self._extract_pricing(item, response)

        item["reservation_type"] = "reservable"
        item["managed_by"] = item.get("managed_by", "")

        if item.get("name"):
            yield item
        else:
            logger.warning("Skipping campground with no name: %s", response.url)

    # ------------------------------------------------------------------
    # JSON-LD
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json_ld(response):
        """Extract campground-related JSON-LD."""
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
        if not item.get("name"):
            item["name"] = ld.get("name", "")
        if not item.get("description"):
            item["description"] = ld.get("description", "")

        address = ld.get("address", {})
        if isinstance(address, dict):
            item.setdefault("address", address.get("streetAddress", ""))
            item.setdefault("city", address.get("addressLocality", ""))
            item.setdefault("state", address.get("addressRegion", ""))
            item.setdefault("zip_code", address.get("postalCode", ""))

        geo = ld.get("geo", {})
        if isinstance(geo, dict):
            if not item.get("latitude"):
                item["latitude"] = self._to_float(geo.get("latitude"))
            if not item.get("longitude"):
                item["longitude"] = self._to_float(geo.get("longitude"))

        item.setdefault("phone", ld.get("telephone", ""))

        rating = ld.get("aggregateRating", {})
        if isinstance(rating, dict):
            item.setdefault("source_rating", self._to_float(rating.get("ratingValue")))
            item.setdefault("source_review_count", self._to_int(rating.get("reviewCount")))

        images = ld.get("image", [])
        if images:
            if isinstance(images, str):
                images = [images]
            item["photos"] = [
                {"url": u, "caption": ""} for u in images[:20] if isinstance(u, str)
            ]

    # ------------------------------------------------------------------
    # HTML extraction
    # ------------------------------------------------------------------

    def _populate_from_html(self, item, response):
        """Extract fields from visible HTML elements."""
        if not item.get("name"):
            item["name"] = (
                response.css("h1.park-name::text").get("")
                or response.css("h1::text").get("")
            ).strip()

        if not item.get("description"):
            item["description"] = (
                response.css("div.park-description p::text").get("")
                or response.css("div.description::text").get("")
                or response.css('meta[name="description"]::attr(content)').get("")
            ).strip()

        # Address block
        if not item.get("address"):
            item["address"] = response.css(
                "span.street-address::text, "
                "div.park-address .address-line-1::text"
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

        # Phone
        if not item.get("phone"):
            item["phone"] = (
                response.css('a[href^="tel:"]::text').get("")
                or response.css("span.phone-number::text").get("")
            ).strip()

        # Email
        if not item.get("email"):
            item["email"] = response.css('a[href^="mailto:"]::text').get("").strip()

        # Coordinates from data attributes or inline script
        if not item.get("latitude") or not item.get("longitude"):
            lat, lng = self._extract_coords(response)
            if lat is not None:
                item["latitude"] = lat
                item["longitude"] = lng

        # Reservation URL
        item["reservation_url"] = (
            response.css('a[href*="reserv"]::attr(href)').get("")
            or response.css('a.reserve-btn::attr(href)').get("")
            or response.css('a.book-now::attr(href)').get("")
        )

    # ------------------------------------------------------------------
    # Good Sam-specific rating
    # ------------------------------------------------------------------

    def _extract_good_sam_rating(self, item, response):
        """
        Good Sam uses a triple rating system (Facilities/Restrooms/Appeal)
        each scored 1-10, displayed as e.g. "9/9.5/8.5".
        We store the combined average as source_rating.
        """
        rating_text = response.css(
            "span.gs-rating::text, "
            "div.rating-value::text, "
            "span.overall-rating::text"
        ).get("").strip()

        if rating_text and not item.get("source_rating"):
            # Try "9/9.5/8.5" format
            parts = rating_text.split("/")
            ratings = []
            for p in parts:
                val = self._to_float(p.strip())
                if val is not None:
                    ratings.append(val)
            if ratings:
                item["source_rating"] = round(sum(ratings) / len(ratings), 1)

        # Review count
        review_count_text = response.css(
            "span.review-count::text, "
            "a.reviews-link::text"
        ).get("").strip()
        if review_count_text and not item.get("source_review_count"):
            item["source_review_count"] = self._to_int(review_count_text)

    # ------------------------------------------------------------------
    # RV-specific data
    # ------------------------------------------------------------------

    def _extract_rv_data(self, item, response):
        """Extract RV-specific information: max length, hookup types, site types."""
        # Max RV length
        max_length_text = response.css(
            "span.max-rv-length::text, "
            "div.rv-length::text, "
            "td:contains('Max RV Length') + td::text, "
            "dt:contains('Max RV Length') + dd::text"
        ).get("").strip()
        if max_length_text:
            item["max_rv_length"] = self._to_int(max_length_text)

        # Also search description-list style tables
        if not item.get("max_rv_length"):
            for row in response.css("tr, div.detail-row"):
                label = row.css("td:first-child::text, dt::text, span.label::text").get("")
                if "rv length" in label.lower() or "max length" in label.lower():
                    value = row.css("td:last-child::text, dd::text, span.value::text").get("")
                    item["max_rv_length"] = self._to_int(value)
                    break

        # Total sites
        total_sites_text = response.css(
            "span.total-sites::text, "
            "td:contains('Total Sites') + td::text, "
            "dt:contains('Total Sites') + dd::text"
        ).get("").strip()
        if total_sites_text:
            item["total_sites"] = self._to_int(total_sites_text)

        # Hookup types from detail table
        hookup_texts = response.css(
            "ul.hookups li::text, "
            "div.hookup-type::text, "
            "span.hookup::text"
        ).getall()
        if hookup_texts:
            hookups = set()
            for text in hookup_texts:
                lower = text.strip().lower()
                if "electric" in lower or "amp" in lower:
                    hookups.add("electric")
                if "water" in lower:
                    hookups.add("water")
                if "sewer" in lower:
                    hookups.add("sewer")
            if hookups:
                item["hookups"] = sorted(hookups)

        # Site types
        site_type_texts = response.css(
            "ul.site-types li::text, "
            "div.site-type::text"
        ).getall()
        if site_type_texts:
            item["site_types"] = self._classify_site_types(site_type_texts)

        # Elevation
        elevation_text = response.css(
            "span.elevation::text, "
            "td:contains('Elevation') + td::text, "
            "dt:contains('Elevation') + dd::text"
        ).get("").strip()
        if elevation_text:
            item["elevation"] = self._to_int(elevation_text)

    # ------------------------------------------------------------------
    # Amenities
    # ------------------------------------------------------------------

    def _extract_amenities(self, item, response):
        """Extract amenities, facilities, and activities."""
        amenity_texts = response.css(
            "ul.amenities li::text, "
            "div.amenity-item::text, "
            "span.amenity-name::text, "
            "div.feature-item::text, "
            "li.amenity::text"
        ).getall()
        amenities = [a.strip().lower() for a in amenity_texts if a.strip()]

        if not item.get("hookups"):
            item["hookups"] = self._extract_hookup_list(amenities)
        if not item.get("facilities"):
            item["facilities"] = self._extract_facility_list(amenities)
        if not item.get("activities"):
            item["activities"] = self._extract_activity_list(amenities)

        # Pets
        page_lower = response.text.lower()
        if "pet friendly" in page_lower or "pets allowed" in page_lower or "pets welcome" in page_lower:
            item["pets_allowed"] = True
        elif "no pets" in page_lower:
            item["pets_allowed"] = False

        # Accessibility
        if "ada" in page_lower or "wheelchair" in page_lower or "accessible" in page_lower:
            item["accessibility"] = True

        # Season
        season_text = response.css(
            "span.season::text, "
            "td:contains('Season') + td::text, "
            "dt:contains('Open') + dd::text"
        ).get("").strip()
        if season_text:
            item["season"] = season_text

    # ------------------------------------------------------------------
    # Photos
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_photos(item, response):
        urls = response.css(
            "div.gallery img::attr(src), "
            "div.photo-gallery img::attr(data-src), "
            "div.carousel img::attr(src), "
            "img.park-photo::attr(src)"
        ).getall()
        item["photos"] = [
            {"url": response.urljoin(u), "caption": ""}
            for u in urls[:20]
            if u and not u.endswith(".svg")
        ]

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------

    def _extract_pricing(self, item, response):
        price_texts = response.css(
            "span.price::text, "
            "div.rate-info span::text, "
            "td:contains('Rate') + td::text, "
            "dt:contains('Rate') + dd::text, "
            "span.nightly-rate::text"
        ).getall()
        prices = []
        for t in price_texts:
            for match in re.findall(r'\$\s*(\d+(?:\.\d{1,2})?)', t):
                val = float(match)
                if 0 < val < 1000:
                    prices.append(val)
        if prices:
            item.setdefault("price_min", min(prices))
            item.setdefault("price_max", max(prices))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _follow_api_results(self, response):
        """Check for embedded JSON data from an internal API."""
        for script in response.css("script::text").getall():
            if "window.__INITIAL_STATE__" in script or "window.__DATA__" in script:
                match = re.search(r'(?:__INITIAL_STATE__|__DATA__)\s*=\s*({.+?});', script, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        logger.debug("Found embedded JSON state data on %s", response.url)
                    except json.JSONDecodeError:
                        pass

    def _extract_coords(self, response):
        """Extract coordinates from data attributes or inline scripts."""
        lat = response.css('[data-lat]::attr(data-lat)').get()
        lng = response.css('[data-lng]::attr(data-lng), [data-lon]::attr(data-lon)').get()
        if lat and lng:
            return self._to_float(lat), self._to_float(lng)

        body = response.text
        lat_match = re.search(r'["\']?(?:lat(?:itude)?)["\']?\s*[:=]\s*(-?\d+\.\d+)', body)
        lng_match = re.search(r'["\']?(?:lng|lon(?:gitude)?)["\']?\s*[:=]\s*(-?\d+\.\d+)', body)
        if lat_match and lng_match:
            return float(lat_match.group(1)), float(lng_match.group(1))

        return None, None

    @staticmethod
    def _extract_source_id(url):
        parts = url.rstrip("/").split("/")
        # Remove .html extension if present
        last = parts[-1].replace(".html", "") if parts else ""
        relevant = [p for p in parts if p and p not in ("campgrounds-rv-parks", "www.goodsam.com", "https:")]
        return "-".join(relevant[-2:]) if len(relevant) >= 2 else last or url

    @staticmethod
    def _classify_site_types(texts):
        mapping = {
            "tent": "tent", "rv": "rv", "cabin": "cabin",
            "pull-thru": "rv", "pull-through": "rv", "back-in": "rv",
            "cottage": "cabin", "lodge": "cabin", "park model": "rv",
        }
        types = set()
        for t in texts:
            key = t.strip().lower()
            for keyword, canonical in mapping.items():
                if keyword in key:
                    types.add(canonical)
        return sorted(types) if types else []

    @staticmethod
    def _extract_hookup_list(amenities):
        keywords = {
            "electric": "electric", "30 amp": "electric", "50 amp": "electric",
            "water hookup": "water", "city water": "water",
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
    def _extract_facility_list(amenities):
        keywords = [
            "restroom", "shower", "laundry", "pool", "wifi", "wi-fi",
            "store", "dump station", "playground", "clubhouse", "rec hall",
            "hot tub", "propane", "cable tv",
        ]
        return sorted({kw for kw in keywords if any(kw in a for a in amenities)})

    @staticmethod
    def _extract_activity_list(amenities):
        keywords = [
            "hiking", "fishing", "swimming", "biking", "kayaking",
            "canoeing", "golf", "mini golf", "horseback", "boating",
            "tennis", "basketball", "volleyball",
        ]
        return sorted({kw for kw in keywords if any(kw in a for a in amenities)})

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
