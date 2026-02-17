"""
Spider for stateparks.org campground listings.

Crawls stateparks.org starting from state directory pages.  Prioritises
high-value camping states (CA, CO, TX, FL, OR, WA) then expands to the
remaining states.

Crawl strategy:
  1. Start from state directory pages.
  2. Follow links to individual state-park pages.
  3. Extract campground details from each park page.

Respects robots.txt and uses conservative request rates.
"""

import json
import logging
import re

import scrapy
from campground_scrapers.items import CampgroundItem

logger = logging.getLogger(__name__)


class StateParksSpider(scrapy.Spider):
    name = "state_parks"
    source_name = "state_parks"
    allowed_domains = ["stateparks.org"]

    # High-value camping states first, then remaining states
    HIGH_VALUE_STATES = [
        "california", "colorado", "texas", "florida", "oregon", "washington",
    ]
    REMAINING_STATES = [
        "alabama", "alaska", "arizona", "arkansas", "connecticut", "delaware",
        "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas",
        "kentucky", "louisiana", "maine", "maryland", "massachusetts",
        "michigan", "minnesota", "mississippi", "missouri", "montana",
        "nebraska", "nevada", "new-hampshire", "new-jersey", "new-mexico",
        "new-york", "north-carolina", "north-dakota", "ohio", "oklahoma",
        "pennsylvania", "rhode-island", "south-carolina", "south-dakota",
        "tennessee", "utah", "vermont", "virginia", "west-virginia",
        "wisconsin", "wyoming",
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DEPTH_LIMIT": 5,
    }

    def start_requests(self):
        """Yield requests for state directory pages, high-value states first."""
        all_states = self.HIGH_VALUE_STATES + self.REMAINING_STATES
        for priority, state_slug in enumerate(all_states):
            # stateparks.org uses URL patterns like /state/california/
            for url_pattern in [
                f"https://www.stateparks.org/{state_slug}/",
                f"https://www.stateparks.org/state/{state_slug}/",
            ]:
                yield scrapy.Request(
                    url_pattern,
                    callback=self.parse_state_directory,
                    meta={"state_slug": state_slug},
                    # Higher priority (lower number) for high-value states
                    priority=-priority,
                    dont_filter=False,
                )

    def parse_state_directory(self, response):
        """Parse a state directory page to find individual park pages."""
        state_slug = response.meta.get("state_slug", "")

        # Find links to individual parks
        park_links = response.css(
            'a[href*="/park/"]::attr(href), '
            'a[href*="/parks/"]::attr(href), '
            'a.park-link::attr(href), '
            'div.park-listing a::attr(href), '
            'h2 a::attr(href), '
            'h3 a::attr(href), '
            'li.park-item a::attr(href), '
            'div.park-card a::attr(href)'
        ).getall()

        seen = set()
        for href in park_links:
            full = response.urljoin(href)
            if full not in seen:
                seen.add(full)
                yield response.follow(
                    href,
                    callback=self.parse_park,
                    meta={"state_slug": state_slug},
                )

        # Also look for campground-specific links
        camping_links = response.css(
            'a[href*="camping"]::attr(href), '
            'a[href*="campground"]::attr(href)'
        ).getall()
        for href in camping_links:
            full = response.urljoin(href)
            if full not in seen:
                seen.add(full)
                yield response.follow(
                    href,
                    callback=self.parse_park,
                    meta={"state_slug": state_slug},
                )

        # Pagination
        next_page = response.css(
            'a[rel="next"]::attr(href), '
            'a.next::attr(href), '
            'li.next a::attr(href), '
            'a[aria-label="Next"]::attr(href)'
        ).get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse_state_directory,
                meta={"state_slug": state_slug},
            )

    def parse_park(self, response):
        """
        Parse an individual state park page.  A single park may have
        multiple campgrounds, or the park page itself may describe the
        camping facilities.
        """
        state_slug = response.meta.get("state_slug", "")

        # Check if there are separate campground sub-pages
        campground_sublinks = response.css(
            'a[href*="campground"]::attr(href), '
            'a[href*="camping"]::attr(href), '
            'a.campground-link::attr(href)'
        ).getall()

        # Filter to links that are children of this park page
        sub_pages = [
            href for href in campground_sublinks
            if href and href != response.url and self._is_subpage(response.url, response.urljoin(href))
        ]

        if sub_pages:
            for href in sub_pages:
                yield response.follow(
                    href,
                    callback=self.parse_campground_page,
                    meta={
                        "state_slug": state_slug,
                        "park_url": response.url,
                        "park_name": response.css("h1::text").get("").strip(),
                    },
                )
        else:
            # The park page itself describes camping -- extract directly
            yield from self._extract_campground(response, state_slug)

    def parse_campground_page(self, response):
        """Parse a dedicated campground sub-page within a park."""
        state_slug = response.meta.get("state_slug", "")
        yield from self._extract_campground(
            response,
            state_slug,
            park_name=response.meta.get("park_name", ""),
        )

    def _extract_campground(self, response, state_slug, park_name=""):
        """Core extraction logic.  Yields a CampgroundItem."""
        item = CampgroundItem()
        item["source"] = self.source_name
        item["source_id"] = self._extract_source_id(response.url)
        item["website"] = response.url

        # --- JSON-LD ---
        json_ld = self._extract_json_ld(response)
        if json_ld:
            self._populate_from_json_ld(item, json_ld)

        # --- HTML extraction ---
        self._populate_from_html(item, response)

        # --- Park name ---
        if not item.get("park_name"):
            item["park_name"] = (
                park_name
                or response.css("h1.park-name::text").get("").strip()
                or response.css("h1::text").get("").strip()
            )

        # If we only have a park name and no campground name, use the park name
        if not item.get("name") and item.get("park_name"):
            item["name"] = f"{item['park_name']} Campground"

        # --- State from slug ---
        if not item.get("state"):
            item["state"] = self._slug_to_state(state_slug)

        # --- Managed by ---
        if not item.get("managed_by"):
            state_name = self._slug_to_state_name(state_slug)
            item["managed_by"] = f"{state_name} State Parks" if state_name else "State Parks"

        # --- Campsite count & types ---
        self._extract_site_info(item, response)

        # --- Amenities & facilities ---
        self._extract_amenities(item, response)

        # --- Season & fees ---
        self._extract_season_and_fees(item, response)

        # --- Photos ---
        self._extract_photos(item, response)

        # --- Coordinates ---
        if not item.get("latitude") or not item.get("longitude"):
            lat, lng = self._extract_coords(response)
            if lat is not None:
                item["latitude"] = lat
                item["longitude"] = lng

        if item.get("name"):
            yield item
        else:
            logger.warning("Skipping park with no name: %s", response.url)

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
                response.css("h1.campground-name::text").get("")
                or response.css("h1.park-name::text").get("")
                or response.css("h1::text").get("")
            ).strip()

        if not item.get("description"):
            item["description"] = (
                response.css("div.park-description p::text").get("")
                or response.css("div.description p::text").get("")
                or response.css("div.about p::text").get("")
                or response.css('meta[name="description"]::attr(content)').get("")
            ).strip()

        # Address
        if not item.get("address"):
            addr_parts = response.css(
                "div.park-address::text, "
                "span.street-address::text, "
                "p.address::text"
            ).getall()
            item["address"] = " ".join(p.strip() for p in addr_parts if p.strip())
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

        # Reservation URL
        res_url = (
            response.css('a[href*="reserv"]::attr(href)').get("")
            or response.css('a.reserve-btn::attr(href)').get("")
            or response.css('a.book-now::attr(href)').get("")
            or response.css('a[href*="reserve"]::attr(href)').get("")
        )
        if res_url:
            item["reservation_url"] = response.urljoin(res_url)

    # ------------------------------------------------------------------
    # Campsite details
    # ------------------------------------------------------------------

    def _extract_site_info(self, item, response):
        """Extract site count and site types."""
        # Total sites -- look in detail tables and text
        for row in response.css("tr, div.detail-row, dl"):
            label = row.css(
                "td:first-child::text, th::text, dt::text, span.label::text"
            ).get("")
            if re.search(r'(total|number of)\s*sites', label, re.IGNORECASE):
                value = row.css(
                    "td:last-child::text, dd::text, span.value::text"
                ).get("")
                count = self._to_int(value)
                if count:
                    item["total_sites"] = count
                break

        # Also search body text for "XX campsites"
        if not item.get("total_sites"):
            body = response.text
            match = re.search(r'(\d+)\s+(?:camp)?sites', body, re.IGNORECASE)
            if match:
                item["total_sites"] = int(match.group(1))

        # Site types
        site_type_texts = response.css(
            "ul.site-types li::text, "
            "div.campsite-type::text, "
            "span.site-type::text"
        ).getall()
        if site_type_texts:
            item["site_types"] = self._classify_site_types(site_type_texts)
        else:
            # Infer from page text
            page_lower = response.text.lower()
            types = []
            if "tent site" in page_lower or "tent camping" in page_lower:
                types.append("tent")
            if "rv site" in page_lower or "rv camping" in page_lower or "rv hookup" in page_lower:
                types.append("rv")
            if "cabin" in page_lower or "yurt" in page_lower:
                types.append("cabin")
            if types:
                item["site_types"] = types

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
        amenity_texts = response.css(
            "ul.amenities li::text, "
            "div.amenity-item::text, "
            "ul.facilities li::text, "
            "ul.features li::text, "
            "div.park-facilities li::text, "
            "span.amenity::text"
        ).getall()
        amenities = [a.strip().lower() for a in amenity_texts if a.strip()]

        # Hookups
        hookup_keywords = {
            "electric": "electric", "30 amp": "electric", "50 amp": "electric",
            "water hookup": "water",
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
            "store", "dump station", "playground", "picnic", "amphitheater",
            "visitor center", "boat ramp", "drinking water",
        ]
        item.setdefault("facilities", sorted(
            {kw for kw in facility_kws if any(kw in a for a in amenities)}
        ))

        # Activities
        activity_kws = [
            "hiking", "fishing", "swimming", "biking", "kayaking",
            "canoeing", "horseback", "boating", "climbing", "wildlife",
            "birdwatching", "cross-country skiing", "snowshoeing",
        ]
        item.setdefault("activities", sorted(
            {kw for kw in activity_kws if any(kw in a for a in amenities)}
        ))

        # Pets
        page_lower = response.text.lower()
        if "pets allowed" in page_lower or "pet friendly" in page_lower or "leashed pets" in page_lower:
            item["pets_allowed"] = True
        elif "no pets" in page_lower:
            item["pets_allowed"] = False

        # Accessibility
        if "ada" in page_lower or "wheelchair" in page_lower or "accessible" in page_lower:
            item["accessibility"] = True

    # ------------------------------------------------------------------
    # Season & fees
    # ------------------------------------------------------------------

    def _extract_season_and_fees(self, item, response):
        # Season / operating dates
        season_text = response.css(
            "span.season::text, "
            "div.open-dates::text, "
            "td:contains('Season') + td::text, "
            "dt:contains('Season') + dd::text, "
            "dt:contains('Open') + dd::text"
        ).get("").strip()
        if season_text:
            item["season"] = season_text
        else:
            # Try to infer from body text
            body = response.text
            match = re.search(
                r'(?:open|season)[:\s]+([A-Z][a-z]+ (?:through|to|-) [A-Z][a-z]+)',
                body,
            )
            if match:
                item["season"] = match.group(1)

        # Reservation type
        page_lower = response.text.lower()
        if "first come" in page_lower or "first-come" in page_lower:
            if "reserv" in page_lower:
                item["reservation_type"] = "mixed"
            else:
                item["reservation_type"] = "first-come"
        elif "reserv" in page_lower:
            item["reservation_type"] = "reservable"

        # Pricing / fees
        fee_texts = response.css(
            "span.fee::text, "
            "td:contains('Fee') + td::text, "
            "dt:contains('Fee') + dd::text, "
            "span.price::text, "
            "div.camping-fee::text, "
            "td:contains('Rate') + td::text"
        ).getall()
        prices = []
        for t in fee_texts:
            for match in re.findall(r'\$\s*(\d+(?:\.\d{1,2})?)', t):
                val = float(match)
                if 0 < val < 500:
                    prices.append(val)
        if prices:
            item.setdefault("price_min", min(prices))
            item.setdefault("price_max", max(prices))

    # ------------------------------------------------------------------
    # Photos
    # ------------------------------------------------------------------

    def _extract_photos(self, item, response):
        if item.get("photos"):
            return
        urls = response.css(
            "div.gallery img::attr(src), "
            "div.photo-gallery img::attr(data-src), "
            "div.park-photos img::attr(src), "
            "div.carousel img::attr(src), "
            "img.park-photo::attr(src)"
        ).getall()
        item["photos"] = [
            {"url": response.urljoin(u), "caption": ""}
            for u in urls[:20]
            if u and not u.endswith(".svg")
        ]

    # ------------------------------------------------------------------
    # Coordinate extraction
    # ------------------------------------------------------------------

    def _extract_coords(self, response):
        # Data attributes
        lat = response.css('[data-lat]::attr(data-lat)').get()
        lng = response.css('[data-lng]::attr(data-lng), [data-lon]::attr(data-lon)').get()
        if lat and lng:
            return self._to_float(lat), self._to_float(lng)

        # Inline script patterns
        body = response.text
        lat_match = re.search(r'["\']?(?:lat(?:itude)?)["\']?\s*[:=]\s*(-?\d+\.\d+)', body)
        lng_match = re.search(r'["\']?(?:lng|lon(?:gitude)?)["\']?\s*[:=]\s*(-?\d+\.\d+)', body)
        if lat_match and lng_match:
            return float(lat_match.group(1)), float(lng_match.group(1))

        # Google Maps embed
        maps_match = re.search(r'maps[^"]*@(-?\d+\.\d+),(-?\d+\.\d+)', body)
        if maps_match:
            return float(maps_match.group(1)), float(maps_match.group(2))

        return None, None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_subpage(parent_url, child_url):
        """Check if child_url is a sub-path of parent_url."""
        parent = parent_url.rstrip("/")
        child = child_url.rstrip("/")
        return child.startswith(parent + "/") and child != parent

    @staticmethod
    def _extract_source_id(url):
        parts = [p for p in url.rstrip("/").split("/") if p and p not in ("https:", "www.stateparks.org")]
        return "-".join(parts[-2:]) if len(parts) >= 2 else (parts[-1] if parts else url)

    STATE_ABBREV = {
        "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
        "california": "CA", "colorado": "CO", "connecticut": "CT",
        "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
        "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
        "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
        "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
        "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
        "montana": "MT", "nebraska": "NE", "nevada": "NV",
        "new-hampshire": "NH", "new-jersey": "NJ", "new-mexico": "NM",
        "new-york": "NY", "north-carolina": "NC", "north-dakota": "ND",
        "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
        "pennsylvania": "PA", "rhode-island": "RI",
        "south-carolina": "SC", "south-dakota": "SD", "tennessee": "TN",
        "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA",
        "washington": "WA", "west-virginia": "WV", "wisconsin": "WI",
        "wyoming": "WY",
    }

    STATE_NAMES = {
        "alabama": "Alabama", "alaska": "Alaska", "arizona": "Arizona",
        "arkansas": "Arkansas", "california": "California",
        "colorado": "Colorado", "connecticut": "Connecticut",
        "delaware": "Delaware", "florida": "Florida", "georgia": "Georgia",
        "hawaii": "Hawaii", "idaho": "Idaho", "illinois": "Illinois",
        "indiana": "Indiana", "iowa": "Iowa", "kansas": "Kansas",
        "kentucky": "Kentucky", "louisiana": "Louisiana", "maine": "Maine",
        "maryland": "Maryland", "massachusetts": "Massachusetts",
        "michigan": "Michigan", "minnesota": "Minnesota",
        "mississippi": "Mississippi", "missouri": "Missouri",
        "montana": "Montana", "nebraska": "Nebraska", "nevada": "Nevada",
        "new-hampshire": "New Hampshire", "new-jersey": "New Jersey",
        "new-mexico": "New Mexico", "new-york": "New York",
        "north-carolina": "North Carolina", "north-dakota": "North Dakota",
        "ohio": "Ohio", "oklahoma": "Oklahoma", "oregon": "Oregon",
        "pennsylvania": "Pennsylvania", "rhode-island": "Rhode Island",
        "south-carolina": "South Carolina", "south-dakota": "South Dakota",
        "tennessee": "Tennessee", "texas": "Texas", "utah": "Utah",
        "vermont": "Vermont", "virginia": "Virginia",
        "washington": "Washington", "west-virginia": "West Virginia",
        "wisconsin": "Wisconsin", "wyoming": "Wyoming",
    }

    @classmethod
    def _slug_to_state(cls, slug):
        """Convert a state slug to its 2-letter abbreviation."""
        return cls.STATE_ABBREV.get(slug.lower(), "")

    @classmethod
    def _slug_to_state_name(cls, slug):
        """Convert a state slug to its full name."""
        return cls.STATE_NAMES.get(slug.lower(), "")

    @staticmethod
    def _classify_site_types(texts):
        mapping = {
            "tent": "tent", "rv": "rv", "cabin": "cabin",
            "yurt": "cabin", "lean-to": "tent", "shelter": "tent",
            "group": "group", "equestrian": "equestrian",
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
