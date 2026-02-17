"""
Spider for Thousand Trails campground listings.

Crawls thousandtrails.com starting from the "Find a Campground" page.
Thousand Trails operates ~80 campground locations across the US, so the total
page count is manageable.

Crawl strategy:
  1. Start from the campground finder page.
  2. Discover individual campground detail links.
  3. Extract structured data from detail pages.

Respects robots.txt and uses conservative request rates.
"""

import json
import logging
import re

import scrapy
from campground_scrapers.items import CampgroundItem

logger = logging.getLogger(__name__)


class ThousandTrailsSpider(scrapy.Spider):
    name = "thousand_trails"
    source_name = "thousand_trails"
    allowed_domains = ["thousandtrails.com"]
    start_urls = [
        "https://www.thousandtrails.com/find-a-campground",
        "https://www.thousandtrails.com/find-a-campground/",
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DEPTH_LIMIT": 4,
    }

    # US states/regions to seed location searches
    REGIONS = [
        "california", "oregon", "washington", "arizona", "colorado",
        "texas", "florida", "georgia", "north-carolina", "south-carolina",
        "virginia", "maryland", "pennsylvania", "new-york", "new-jersey",
        "connecticut", "massachusetts", "michigan", "ohio", "indiana",
        "illinois", "wisconsin", "minnesota", "missouri", "tennessee",
        "alabama", "louisiana", "mississippi", "idaho", "montana",
        "nevada", "utah", "new-mexico", "oklahoma",
    ]

    def parse(self, response):
        """
        Parse the campground finder page.  Strategies:

        1. Follow any campground detail links visible on the page.
        2. Look for an embedded JSON data source (API or __NEXT_DATA__).
        3. Seed regional search URLs as fallback.
        """
        # Strategy 1: direct links to campground detail pages
        campground_links = response.css(
            'a[href*="/campgrounds/"]::attr(href), '
            'a[href*="/rv-resorts/"]::attr(href), '
            'a.campground-link::attr(href), '
            'div.location-card a::attr(href), '
            'a.park-card-link::attr(href)'
        ).getall()

        seen = set()
        for href in campground_links:
            full = response.urljoin(href)
            if full not in seen and self._is_detail_url(href):
                seen.add(full)
                yield response.follow(href, callback=self.parse_campground)

        # Strategy 2: embedded JSON data with location list
        locations = self._extract_embedded_locations(response)
        for loc in locations:
            url = loc.get("url") or loc.get("link") or loc.get("detailUrl")
            if url:
                full = response.urljoin(url)
                if full not in seen:
                    seen.add(full)
                    yield scrapy.Request(
                        full,
                        callback=self.parse_campground,
                        meta={"prefetched": loc},
                    )

        # Strategy 3: follow links to state/region listing pages
        region_links = response.css(
            'a[href*="/find-a-campground/"]::attr(href), '
            'a[href*="/campgrounds-near/"]::attr(href)'
        ).getall()
        for href in region_links:
            full = response.urljoin(href)
            if full not in seen:
                seen.add(full)
                yield response.follow(href, callback=self.parse_region)

        # Strategy 4: seed regional URLs
        for region in self.REGIONS:
            url = f"https://www.thousandtrails.com/find-a-campground/{region}"
            if url not in seen:
                yield scrapy.Request(url, callback=self.parse_region, priority=-1)

    def parse_region(self, response):
        """Parse a regional listing page for campground links."""
        links = response.css(
            'a[href*="/campgrounds/"]::attr(href), '
            'a[href*="/rv-resorts/"]::attr(href), '
            'div.location-card a::attr(href), '
            'a.park-card-link::attr(href), '
            'h2 a::attr(href), '
            'h3 a::attr(href)'
        ).getall()

        for href in links:
            if self._is_detail_url(href):
                yield response.follow(href, callback=self.parse_campground)

        # Pagination
        next_page = response.css(
            'a[rel="next"]::attr(href), '
            'a.next-page::attr(href)'
        ).get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_region)

    def parse_campground(self, response):
        """Parse an individual Thousand Trails campground detail page."""
        item = CampgroundItem()
        item["source"] = self.source_name
        item["source_id"] = self._extract_source_id(response.url)
        item["website"] = response.url

        # Use any prefetched data from the finder page JSON
        prefetched = response.meta.get("prefetched", {})
        if prefetched:
            self._populate_from_prefetched(item, prefetched)

        # --- JSON-LD ---
        json_ld = self._extract_json_ld(response)
        if json_ld:
            self._populate_from_json_ld(item, json_ld)

        # --- HTML extraction ---
        self._populate_from_html(item, response)

        # --- Amenities ---
        self._extract_amenities(item, response)

        # --- Photos ---
        self._extract_photos(item, response)

        # --- Activities ---
        self._extract_activities_section(item, response)

        # --- Pricing ---
        self._extract_pricing(item, response)

        # Default managed_by
        if not item.get("managed_by"):
            item["managed_by"] = "Thousand Trails / Encore"

        item.setdefault("reservation_type", "reservable")

        if item.get("name"):
            yield item
        else:
            logger.warning("Skipping campground with no name: %s", response.url)

    # ------------------------------------------------------------------
    # Prefetched data from finder-page JSON
    # ------------------------------------------------------------------

    def _populate_from_prefetched(self, item, data):
        """Fill item from pre-extracted JSON data."""
        item.setdefault("name", data.get("name", ""))
        item.setdefault("city", data.get("city", ""))
        item.setdefault("state", data.get("state", ""))
        item.setdefault("address", data.get("address", ""))
        item.setdefault("zip_code", data.get("zipCode", "") or data.get("zip", ""))

        lat = self._to_float(data.get("latitude") or data.get("lat"))
        lng = self._to_float(data.get("longitude") or data.get("lng") or data.get("lon"))
        if lat is not None:
            item.setdefault("latitude", lat)
        if lng is not None:
            item.setdefault("longitude", lng)

        item.setdefault("phone", data.get("phone", ""))

    # ------------------------------------------------------------------
    # JSON-LD
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json_ld(response):
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
        item.setdefault("name", ld.get("name", ""))
        item.setdefault("description", ld.get("description", ""))

        address = ld.get("address", {})
        if isinstance(address, dict):
            item.setdefault("address", address.get("streetAddress", ""))
            item.setdefault("city", address.get("addressLocality", ""))
            item.setdefault("state", address.get("addressRegion", ""))
            item.setdefault("zip_code", address.get("postalCode", ""))

        geo = ld.get("geo", {})
        if isinstance(geo, dict):
            lat = self._to_float(geo.get("latitude"))
            lng = self._to_float(geo.get("longitude"))
            if lat is not None:
                item.setdefault("latitude", lat)
            if lng is not None:
                item.setdefault("longitude", lng)

        item.setdefault("phone", ld.get("telephone", ""))

        rating = ld.get("aggregateRating", {})
        if isinstance(rating, dict):
            item.setdefault("source_rating", self._to_float(rating.get("ratingValue")))
            item.setdefault("source_review_count", self._to_int(rating.get("reviewCount")))

        images = ld.get("image", [])
        if images and not item.get("photos"):
            if isinstance(images, str):
                images = [images]
            item["photos"] = [
                {"url": u, "caption": ""} for u in images[:20] if isinstance(u, str)
            ]

    # ------------------------------------------------------------------
    # HTML extraction
    # ------------------------------------------------------------------

    def _populate_from_html(self, item, response):
        if not item.get("name"):
            item["name"] = (
                response.css("h1.park-name::text").get("")
                or response.css("h1.resort-name::text").get("")
                or response.css("h1::text").get("")
            ).strip()

        if not item.get("description"):
            item["description"] = (
                response.css("div.park-description p::text").get("")
                or response.css("div.resort-description::text").get("")
                or response.css("div.about-section p::text").get("")
                or response.css('meta[name="description"]::attr(content)').get("")
            ).strip()

        # Address block
        if not item.get("address"):
            item["address"] = response.css(
                "span.street-address::text, "
                "div.address-line::text, "
                "p.park-address::text"
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
                or response.css("span.phone::text").get("")
            ).strip()

        # Email
        if not item.get("email"):
            item["email"] = response.css('a[href^="mailto:"]::text').get("").strip()

        # Coordinates
        if not item.get("latitude") or not item.get("longitude"):
            lat, lng = self._extract_coords(response)
            if lat is not None:
                item["latitude"] = lat
                item["longitude"] = lng

        # Reservation link
        res_url = (
            response.css('a[href*="reserv"]::attr(href)').get("")
            or response.css('a.book-now::attr(href)').get("")
            or response.css('a.reserve-btn::attr(href)').get("")
        )
        if res_url:
            item["reservation_url"] = response.urljoin(res_url)

        # Total sites
        sites_text = response.css(
            "span.total-sites::text, "
            "div.site-count::text"
        ).get("").strip()
        if sites_text:
            item["total_sites"] = self._to_int(sites_text)

        # Season
        season_text = response.css(
            "span.season::text, "
            "div.open-dates::text, "
            "span.operating-season::text"
        ).get("").strip()
        if season_text:
            item["season"] = season_text

    # ------------------------------------------------------------------
    # Amenities
    # ------------------------------------------------------------------

    def _extract_amenities(self, item, response):
        amenity_texts = response.css(
            "ul.amenities li::text, "
            "div.amenity-item::text, "
            "div.amenity-name::text, "
            "ul.feature-list li::text, "
            "div.resort-amenities li::text, "
            "span.amenity::text"
        ).getall()
        amenities = [a.strip().lower() for a in amenity_texts if a.strip()]

        # Hookups
        hookup_keywords = {
            "electric": "electric", "30 amp": "electric", "50 amp": "electric",
            "water hookup": "water", "water hook": "water",
            "sewer": "sewer", "full hookup": "sewer",
        }
        hookups = set()
        for a in amenities:
            for kw, hookup in hookup_keywords.items():
                if kw in a:
                    hookups.add(hookup)
        if any("full hookup" in a for a in amenities):
            hookups.update(["electric", "water", "sewer"])
        item.setdefault("hookups", sorted(hookups))

        # Facilities
        facility_kws = [
            "restroom", "shower", "laundry", "pool", "wifi", "wi-fi",
            "store", "dump station", "playground", "clubhouse", "rec hall",
            "hot tub", "fitness", "game room", "mini golf",
        ]
        item.setdefault("facilities", sorted(
            {kw for kw in facility_kws if any(kw in a for a in amenities)}
        ))

        # Site types
        site_type_texts = response.css(
            "div.site-types li::text, "
            "ul.accommodation-types li::text"
        ).getall()
        if site_type_texts:
            item.setdefault("site_types", self._classify_site_types(site_type_texts))

        # Max RV length
        for row in response.css("tr, div.detail-row, div.spec-item"):
            label = row.css(
                "td:first-child::text, dt::text, span.label::text, div.spec-label::text"
            ).get("")
            if "rv length" in label.lower() or "max length" in label.lower():
                value = row.css(
                    "td:last-child::text, dd::text, span.value::text, div.spec-value::text"
                ).get("")
                rv_len = self._to_int(value)
                if rv_len:
                    item["max_rv_length"] = rv_len
                break

        # Pets
        page_lower = response.text.lower()
        if "pet friendly" in page_lower or "pets welcome" in page_lower or "dog park" in page_lower:
            item["pets_allowed"] = True
        elif "no pets" in page_lower:
            item["pets_allowed"] = False

        # Accessibility
        if "ada" in page_lower or "wheelchair" in page_lower or "accessible" in page_lower:
            item["accessibility"] = True

    # ------------------------------------------------------------------
    # Activities
    # ------------------------------------------------------------------

    def _extract_activities_section(self, item, response):
        activity_texts = response.css(
            "ul.activities li::text, "
            "div.activity-item::text, "
            "div.things-to-do li::text, "
            "section.activities li::text"
        ).getall()
        activities_lower = [a.strip().lower() for a in activity_texts if a.strip()]

        activity_kws = [
            "hiking", "fishing", "swimming", "biking", "kayaking",
            "canoeing", "horseback", "golf", "mini golf", "boating",
            "tennis", "basketball", "volleyball", "horseshoes",
            "shuffleboard", "pickleball",
        ]
        found = sorted({kw for kw in activity_kws if any(kw in a for a in activities_lower)})
        if found:
            # Merge with any already-extracted activities
            existing = set(item.get("activities", []))
            existing.update(found)
            item["activities"] = sorted(existing)

    # ------------------------------------------------------------------
    # Photos
    # ------------------------------------------------------------------

    def _extract_photos(self, item, response):
        if item.get("photos"):
            return
        urls = response.css(
            "div.gallery img::attr(src), "
            "div.photo-gallery img::attr(data-src), "
            "div.carousel img::attr(src), "
            "div.hero-image img::attr(src), "
            "img.resort-photo::attr(src)"
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
        if item.get("price_min"):
            return
        price_texts = response.css(
            "span.price::text, "
            "div.rate-info::text, "
            "span.nightly-rate::text, "
            "div.pricing span::text"
        ).getall()
        prices = []
        for t in price_texts:
            for match in re.findall(r'\$\s*(\d+(?:\.\d{1,2})?)', t):
                val = float(match)
                if 0 < val < 1000:
                    prices.append(val)
        if prices:
            item["price_min"] = min(prices)
            item["price_max"] = max(prices)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_embedded_locations(self, response):
        """Try to extract a list of locations from embedded JSON."""
        locations = []
        for script in response.css("script::text").getall():
            # Look for JSON arrays of location objects
            for pattern in [
                r'locations\s*[:=]\s*(\[.+?\])\s*[;,]',
                r'campgrounds\s*[:=]\s*(\[.+?\])\s*[;,]',
                r'parks\s*[:=]\s*(\[.+?\])\s*[;,]',
                r'resorts\s*[:=]\s*(\[.+?\])\s*[;,]',
            ]:
                match = re.search(pattern, script, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        if isinstance(data, list):
                            locations.extend(data)
                    except json.JSONDecodeError:
                        continue

            # Also check __NEXT_DATA__
            if "__NEXT_DATA__" in script:
                try:
                    nd_match = re.search(r'__NEXT_DATA__\s*=\s*({.+?})\s*;?\s*</script>', script, re.DOTALL)
                    if nd_match:
                        data = json.loads(nd_match.group(1))
                        page_props = data.get("props", {}).get("pageProps", {})
                        for key in ("locations", "campgrounds", "parks", "resorts"):
                            locs = page_props.get(key, [])
                            if isinstance(locs, list):
                                locations.extend(locs)
                except (json.JSONDecodeError, TypeError):
                    pass

        return [loc for loc in locations if isinstance(loc, dict)]

    @staticmethod
    def _is_detail_url(href):
        """Check if a URL looks like a campground detail page."""
        if not href:
            return False
        path = href.strip("/").lower()
        # Detail pages typically have a specific campground name slug
        detail_patterns = ["/campgrounds/", "/rv-resorts/", "/resort/"]
        if any(p in path for p in detail_patterns):
            # Ensure it's not just a category/region page
            parts = path.split("/")
            return len(parts) >= 2
        return False

    @staticmethod
    def _extract_source_id(url):
        parts = [p for p in url.rstrip("/").split("/") if p]
        # Use the last meaningful path segment
        for skip in ("https:", "www.thousandtrails.com"):
            if skip in parts:
                parts.remove(skip)
        return parts[-1] if parts else url

    def _extract_coords(self, response):
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
    def _classify_site_types(texts):
        mapping = {
            "tent": "tent", "rv": "rv", "cabin": "cabin",
            "cottage": "cabin", "lodge": "cabin", "pull-thru": "rv",
            "pull-through": "rv", "back-in": "rv", "glamping": "glamping",
        }
        types = set()
        for t in texts:
            key = t.strip().lower()
            for keyword, canonical in mapping.items():
                if keyword in key:
                    types.add(canonical)
        return sorted(types) if types else []

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
