"""
Tests for the transforms.normalizer module.

Covers slug generation, HTML stripping, and the three normalizer
functions (Recreation.gov, NPS, scraped) including edge cases.
"""

import sys
from pathlib import Path

_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from transforms.normalizer import (
    generate_slug,
    normalize_nps,
    normalize_recreation_gov,
    normalize_scraped,
    strip_html,
)


# ---------------------------------------------------------------------------
# Sample fixture data
# ---------------------------------------------------------------------------

SAMPLE_RIDB_FACILITY = {
    "FacilityID": "232447",
    "FacilityName": "Yosemite Valley Campground",
    "FacilityDescription": "<p>Beautiful campground</p>",
    "FacilityTypeDescription": "Campground",
    "FacilityPhone": "209-555-1234",
    "FacilityEmail": "test@recreation.gov",
    "FacilityReservationURL": "https://www.recreation.gov/camping/campgrounds/232447",
    "FacilityLatitude": 37.7396,
    "FacilityLongitude": -119.5711,
    "FacilityDirections": "<b>Take Hwy 41 north</b>",
    "FacilityUseFeeDescription": "Fee: $26/night",
    "FacilityAdaAccess": "Accessible sites available",
    "Reservable": True,
    "LastUpdatedDate": "2024-01-15",
    "FACILITYADDRESS": [
        {
            "FacilityAddressType": "Physical",
            "City": "Yosemite Valley",
            "AddressStateCode": "CA",
            "PostalCode": "95389",
            "FacilityStreetAddress1": "9035 Village Dr",
        }
    ],
    "ORGANIZATION": [{"OrgName": "National Park Service"}],
    "ACTIVITY": [
        {"ActivityName": "Camping"},
        {"ActivityName": "Hiking"},
    ],
    "CAMPSITE": [
        {"CampsiteType": "STANDARD NONELECTRIC"},
        {"CampsiteType": "TENT ONLY NONELECTRIC"},
    ],
    "MEDIA": [
        {"URL": "https://example.com/photo.jpg", "Title": "Main photo"},
        {"URL": "https://example.com/photo2.jpg", "Title": "View"},
    ],
}

SAMPLE_NPS_CAMPGROUND = {
    "id": "ABC123",
    "name": "Elkmont Campground",
    "parkCode": "grsm",
    "description": "Historic campground in the Smokies",
    "latitude": "35.123",
    "longitude": "-83.456",
    "regulationsOverview": "",
    "numberOfSitesReservable": "220",
    "numberOfSitesFirstComeFirstServe": "0",
    "campsites": {
        "totalSites": "220",
        "tentOnly": "100",
        "electricalHookups": "0",
        "rvOnly": "50",
        "walkBoatTo": "0",
        "group": "10",
        "horse": "0",
        "other": "0",
    },
    "addresses": [
        {
            "type": "Physical",
            "line1": "434 Elkmont Rd",
            "city": "Gatlinburg",
            "stateCode": "TN",
            "postalCode": "37738",
        }
    ],
    "images": [
        {"url": "https://example.com/nps.jpg", "title": "Main view"}
    ],
    "contacts": {
        "phoneNumbers": [{"phoneNumber": "865-555-1234"}],
        "emailAddresses": [{"emailAddress": "info@nps.gov"}],
    },
    "fees": [{"cost": "25.00", "title": "Standard Site"}],
    "operatingHours": [{"description": "Open March through November"}],
    "reservationUrl": "https://www.recreation.gov/camping/campgrounds/ABC123",
    "lastIndexedDate": "2024-06-01",
}


# ===================================================================
# generate_slug
# ===================================================================

class TestGenerateSlug:
    """Tests for the generate_slug helper."""

    def test_basic_slug(self):
        result = generate_slug("Happy Valley Camp", "CA")
        assert result == "happy-valley-camp-ca"

    def test_with_city(self):
        result = generate_slug("Pine Creek", "OR", city="Bend")
        assert result == "pine-creek-bend-or"

    def test_special_characters(self):
        result = generate_slug("Camp #1 (North)", "WA")
        assert result == "camp-1-north-wa"

    def test_unicode_characters(self):
        """Unicode chars (accented letters) are normalized to ASCII."""
        result = generate_slug("Cafe del Bosque", "NM")
        assert result == "cafe-del-bosque-nm"

        result = generate_slug("Riviere Sauvage", "ME")
        assert result == "riviere-sauvage-me"

    def test_consecutive_special_chars_collapsed(self):
        result = generate_slug("Camp --- Valley *** Creek", "CA")
        assert result == "camp-valley-creek-ca"

    def test_leading_trailing_hyphens_stripped(self):
        result = generate_slug("  --Camp--  ", "TX")
        assert result == "camp-tx"

    def test_empty_name_returns_empty(self):
        result = generate_slug("", "CA")
        assert result == ""

    def test_empty_state_still_works(self):
        result = generate_slug("Some Camp", "")
        # With empty state, the slug still contains the name
        assert "some-camp" in result


# ===================================================================
# strip_html
# ===================================================================

class TestStripHtml:
    """Tests for the strip_html helper."""

    def test_removes_tags(self):
        result = strip_html("<p>Hello <b>World</b></p>")
        assert result == "Hello World"

    def test_unescapes_entities(self):
        result = strip_html("Fish &amp; Chips &lt;3")
        assert result == "Fish & Chips <3"

    def test_handles_none(self):
        result = strip_html(None)
        assert result == ""

    def test_handles_empty_string(self):
        result = strip_html("")
        assert result == ""

    def test_strips_whitespace(self):
        result = strip_html("  <span>  hello  </span>  ")
        assert result == "hello"

    def test_nested_tags(self):
        result = strip_html("<div><p><a href='#'>Link text</a></p></div>")
        assert result == "Link text"

    def test_self_closing_tags(self):
        result = strip_html("Line one<br/>Line two")
        assert result == "Line oneLine two"


# ===================================================================
# normalize_recreation_gov
# ===================================================================

class TestNormalizeRecreationGov:
    """Tests for normalize_recreation_gov."""

    @pytest.fixture()
    def normalized(self):
        """Return a normalized document from the sample RIDB facility."""
        return normalize_recreation_gov(
            SAMPLE_RIDB_FACILITY,
            campsites=SAMPLE_RIDB_FACILITY["CAMPSITE"],
        )

    # -- _doc_id ---
    def test_doc_id_format(self, normalized):
        assert normalized["_doc_id"] == "recreation_gov_232447"

    # -- top-level fields ---
    def test_name(self, normalized):
        assert normalized["name"] == "Yosemite Valley Campground"

    def test_slug_generated(self, normalized):
        assert "yosemite" in normalized["slug"]
        assert "ca" in normalized["slug"]

    def test_description_html_stripped(self, normalized):
        assert normalized["description"] == "Beautiful campground"
        assert "<p>" not in normalized["description"]

    def test_source_field(self, normalized):
        assert normalized["source"] == "recreation_gov"

    def test_source_id(self, normalized):
        assert normalized["sourceId"] == "232447"

    # -- location ---
    def test_location_address(self, normalized):
        loc = normalized["location"]
        assert loc["address"] == "9035 Village Dr"
        assert loc["city"] == "Yosemite Valley"
        assert loc["state"] == "CA"
        assert loc["zip"] == "95389"
        assert loc["country"] == "US"

    def test_location_coordinates(self, normalized):
        loc = normalized["location"]
        assert loc["latitude"] == 37.7396
        assert loc["longitude"] == -119.5711
        assert loc["geopoint"] is not None

    def test_location_region(self, normalized):
        assert normalized["location"]["region"] == "Pacific"

    def test_location_state_full_name(self, normalized):
        assert normalized["location"]["stateFullName"] == "California"

    # -- contact ---
    def test_contact_phone(self, normalized):
        assert normalized["contact"]["phone"] == "209-555-1234"

    def test_contact_email(self, normalized):
        assert normalized["contact"]["email"] == "test@recreation.gov"

    def test_contact_reservation_url(self, normalized):
        url = normalized["contact"]["reservationUrl"]
        assert "232447" in url
        assert url.startswith("https://www.recreation.gov/camping/campgrounds/")

    # -- details ---
    def test_details_total_sites(self, normalized):
        assert normalized["details"]["totalSites"] == 2

    def test_details_site_types(self, normalized):
        site_types = normalized["details"]["siteTypes"]
        assert "STANDARD NONELECTRIC" in site_types
        assert "TENT ONLY NONELECTRIC" in site_types

    def test_details_facility_type(self, normalized):
        assert normalized["details"]["facilityType"] == "Campground"

    def test_details_reservable(self, normalized):
        assert normalized["details"]["reservable"] is True

    def test_details_directions_html_stripped(self, normalized):
        assert "<b>" not in normalized["details"]["directions"]
        assert "Take Hwy 41 north" in normalized["details"]["directions"]

    # -- amenities ---
    def test_amenities_hookups_default_false(self, normalized):
        hookups = normalized["amenities"]["hookups"]
        # Sample campsites have no hookup attributes
        assert hookups["electric"] is False
        assert hookups["water"] is False
        assert hookups["sewer"] is False

    def test_amenities_activities(self, normalized):
        assert "Camping" in normalized["amenities"]["activities"]
        assert "Hiking" in normalized["amenities"]["activities"]

    # -- photos ---
    def test_photos(self, normalized):
        assert len(normalized["photos"]) == 2
        assert normalized["photos"][0]["url"] == "https://example.com/photo.jpg"
        assert normalized["photos"][0]["caption"] == "Main photo"

    # -- ratings ---
    def test_ratings_initialised_to_zero(self, normalized):
        assert normalized["ratings"]["avgRating"] == 0
        assert normalized["ratings"]["totalReviews"] == 0

    # -- metadata ---
    def test_metadata_fields(self, normalized):
        meta = normalized["metadata"]
        assert isinstance(meta["createdAt"], datetime)
        assert isinstance(meta["updatedAt"], datetime)
        assert isinstance(meta["lastSyncedAt"], datetime)
        assert meta["isActive"] is True
        assert meta["isVerified"] is True
        assert meta["syncSource"] == "pipeline_v1"
        assert meta["sourceLastUpdated"] == "2024-01-15"


# ===================================================================
# normalize_recreation_gov – edge cases
# ===================================================================

class TestNormalizeRecreationGovEdgeCases:
    """Edge cases for normalize_recreation_gov."""

    def test_missing_address(self):
        """Facility with no FACILITYADDRESS still normalizes."""
        facility = {"FacilityID": "1", "FacilityName": "No Addr Camp"}
        result = normalize_recreation_gov(facility)
        assert result["location"]["city"] == ""
        assert result["location"]["state"] == ""

    def test_missing_media(self):
        """Facility with no MEDIA produces empty photos list."""
        facility = {"FacilityID": "2", "FacilityName": "No Media Camp"}
        result = normalize_recreation_gov(facility)
        assert result["photos"] == []

    def test_none_campsites(self):
        """Passing campsites=None produces zero-count summary."""
        facility = {"FacilityID": "3", "FacilityName": "Empty Camp"}
        result = normalize_recreation_gov(facility, campsites=None)
        assert result["details"]["totalSites"] == 0

    def test_empty_description(self):
        """Empty or missing description results in empty string."""
        facility = {"FacilityID": "4", "FacilityName": "Bare Camp"}
        result = normalize_recreation_gov(facility)
        assert result["description"] == ""

    def test_none_coordinates(self):
        """Missing lat/lng results in None geopoint and None coords."""
        facility = {"FacilityID": "5", "FacilityName": "No Coords Camp"}
        result = normalize_recreation_gov(facility)
        assert result["location"]["geopoint"] is None
        assert result["location"]["latitude"] is None
        assert result["location"]["longitude"] is None

    def test_empty_facility_id(self):
        """An empty FacilityID still generates a doc_id."""
        facility = {"FacilityName": "Mystery Camp"}
        result = normalize_recreation_gov(facility)
        assert result["_doc_id"] == "recreation_gov_"


# ===================================================================
# normalize_nps
# ===================================================================

class TestNormalizeNps:
    """Tests for normalize_nps."""

    @pytest.fixture()
    def normalized(self):
        return normalize_nps(SAMPLE_NPS_CAMPGROUND)

    def test_doc_id_format(self, normalized):
        assert normalized["_doc_id"] == "nps_ABC123"

    def test_name(self, normalized):
        assert normalized["name"] == "Elkmont Campground"

    def test_source(self, normalized):
        assert normalized["source"] == "nps"

    def test_source_id(self, normalized):
        assert normalized["sourceId"] == "ABC123"

    def test_description(self, normalized):
        assert normalized["description"] == "Historic campground in the Smokies"

    def test_location_address(self, normalized):
        loc = normalized["location"]
        assert loc["address"] == "434 Elkmont Rd"
        assert loc["city"] == "Gatlinburg"
        assert loc["state"] == "TN"
        assert loc["zip"] == "37738"

    def test_location_coordinates(self, normalized):
        loc = normalized["location"]
        assert loc["latitude"] == 35.123
        assert loc["longitude"] == -83.456

    def test_location_region(self, normalized):
        assert normalized["location"]["region"] == "Southeast"

    def test_contact_phone(self, normalized):
        assert normalized["contact"]["phone"] == "865-555-1234"

    def test_contact_email(self, normalized):
        assert normalized["contact"]["email"] == "info@nps.gov"

    def test_contact_reservation_url(self, normalized):
        assert "ABC123" in normalized["contact"]["reservationUrl"]

    def test_details_total_sites(self, normalized):
        assert normalized["details"]["totalSites"] == 220

    def test_details_site_types(self, normalized):
        site_types = normalized["details"]["siteTypes"]
        assert site_types["tentOnly"] == 100
        assert site_types["rvOnly"] == 50
        assert site_types["group"] == 10

    def test_details_season(self, normalized):
        assert normalized["details"]["season"] == "Open March through November"

    def test_details_fees_description(self, normalized):
        assert "Standard Site" in normalized["details"]["feesDescription"]
        assert "$25.00" in normalized["details"]["feesDescription"]

    def test_photos(self, normalized):
        assert len(normalized["photos"]) == 1
        assert normalized["photos"][0]["url"] == "https://example.com/nps.jpg"
        assert normalized["photos"][0]["caption"] == "Main view"

    def test_ratings_initialised_to_zero(self, normalized):
        assert normalized["ratings"]["avgRating"] == 0
        assert normalized["ratings"]["totalReviews"] == 0

    def test_metadata(self, normalized):
        meta = normalized["metadata"]
        assert meta["isActive"] is True
        assert meta["syncSource"] == "pipeline_v1"
        assert meta["sourceLastUpdated"] == "2024-06-01"


class TestNormalizeNpsEdgeCases:
    """Edge cases for normalize_nps."""

    def test_missing_contacts(self):
        """NPS record with no contacts still normalizes."""
        cg = {"id": "X1", "name": "No Contact Camp"}
        result = normalize_nps(cg)
        assert result["contact"]["phone"] == ""
        assert result["contact"]["email"] == ""

    def test_missing_addresses(self):
        """NPS record with no addresses still normalizes."""
        cg = {"id": "X2", "name": "No Addr Camp"}
        result = normalize_nps(cg)
        assert result["location"]["city"] == ""

    def test_missing_fees(self):
        """NPS record with no fees produces empty description."""
        cg = {"id": "X3", "name": "Free Camp"}
        result = normalize_nps(cg)
        assert result["details"]["feesDescription"] == ""

    def test_missing_operating_hours(self):
        """NPS record with no operatingHours produces empty season."""
        cg = {"id": "X4", "name": "Year Round Camp"}
        result = normalize_nps(cg)
        assert result["details"]["season"] == ""

    def test_zero_electrical_hookups(self):
        """electricalHookups=0 sets electric hookup to False."""
        cg = {
            "id": "X5",
            "name": "No Hookup Camp",
            "campsites": {"totalSites": "10", "electricalHookups": "0"},
        }
        result = normalize_nps(cg)
        assert result["amenities"]["hookups"]["electric"] is False


# ===================================================================
# normalize_scraped
# ===================================================================

class TestNormalizeScraped:
    """Tests for normalize_scraped."""

    def test_basic_normalisation(self):
        item = {
            "source_id": "koa-123",
            "name": "KOA Riverside",
            "description": "<i>Nice spot</i>",
            "state": "Oregon",
            "city": "Portland",
            "latitude": 45.5,
            "longitude": -122.6,
            "phone": "503-555-0000",
            "email": "info@koa.com",
            "total_sites": 50,
        }
        result = normalize_scraped(item, "koa")

        assert result["_doc_id"] == "koa_koa-123"
        assert result["name"] == "KOA Riverside"
        assert result["source"] == "koa"
        assert result["description"] == "Nice spot"
        assert result["location"]["state"] == "OR"
        assert result["location"]["stateFullName"] == "Oregon"
        assert result["details"]["totalSites"] == 50

    def test_photos_as_list_of_strings(self):
        item = {
            "source_id": "hc-1",
            "name": "Hipcamp Spot",
            "photos": ["https://img1.jpg", "https://img2.jpg"],
        }
        result = normalize_scraped(item, "hipcamp")
        assert len(result["photos"]) == 2
        assert result["photos"][0]["url"] == "https://img1.jpg"
        assert result["photos"][0]["caption"] == ""

    def test_photos_as_list_of_dicts(self):
        item = {
            "source_id": "hc-2",
            "name": "Photo Camp",
            "photos": [
                {"url": "https://img.jpg", "caption": "Sunset view"},
            ],
        }
        result = normalize_scraped(item, "hipcamp")
        assert result["photos"][0]["url"] == "https://img.jpg"
        assert result["photos"][0]["caption"] == "Sunset view"

    def test_amenities_as_list(self):
        item = {
            "source_id": "x1",
            "name": "Amenity Camp",
            "amenities": ["WiFi", "Showers", "Laundry"],
        }
        result = normalize_scraped(item, "custom")
        assert result["amenities"]["facilities"] == ["WiFi", "Showers", "Laundry"]

    def test_amenities_as_dict(self):
        item = {
            "source_id": "x2",
            "name": "Dict Amenity Camp",
            "amenities": {"WiFi": True, "Pool": True},
        }
        result = normalize_scraped(item, "custom")
        assert "WiFi" in result["amenities"]["facilities"]
        assert "Pool" in result["amenities"]["facilities"]

    def test_hookups(self):
        item = {
            "source_id": "x3",
            "name": "Full Hookup Camp",
            "hookups": {"electric": True, "water": True, "sewer": False},
        }
        result = normalize_scraped(item, "custom")
        assert result["amenities"]["hookups"]["electric"] is True
        assert result["amenities"]["hookups"]["water"] is True
        assert result["amenities"]["hookups"]["sewer"] is False

    def test_ratings_from_item(self):
        """Scraped items can carry their own ratings."""
        item = {
            "source_id": "x4",
            "name": "Rated Camp",
            "avg_rating": 4.5,
            "total_reviews": 120,
        }
        result = normalize_scraped(item, "yelp")
        assert result["ratings"]["avgRating"] == 4.5
        assert result["ratings"]["totalReviews"] == 120


class TestNormalizeScrapedEdgeCases:
    """Edge cases for normalize_scraped."""

    def test_missing_all_fields(self):
        """An empty dict still produces a valid structure."""
        result = normalize_scraped({}, "unknown")
        assert result["_doc_id"] == "unknown_"
        assert result["name"] == ""
        assert result["location"]["state"] == ""
        assert result["details"]["totalSites"] == 0

    def test_none_values_in_item(self):
        """None values for optional fields are handled gracefully."""
        item = {
            "source_id": "n1",
            "name": None,
            "description": None,
            "photos": None,
            "amenities": None,
            "total_sites": None,
        }
        result = normalize_scraped(item, "test")
        assert result["name"] is None or result["name"] == ""
        assert result["photos"] == []
        assert result["details"]["totalSites"] == 0

    def test_invalid_total_sites(self):
        """Non-numeric total_sites defaults to 0."""
        item = {"source_id": "n2", "name": "Bad Sites", "total_sites": "many"}
        result = normalize_scraped(item, "test")
        assert result["details"]["totalSites"] == 0

    def test_empty_string_source_id(self):
        item = {"source_id": "", "name": "No ID Camp"}
        result = normalize_scraped(item, "test")
        assert result["_doc_id"] == "test_"

    def test_country_defaults_to_us(self):
        item = {"source_id": "c1", "name": "US Camp"}
        result = normalize_scraped(item, "test")
        assert result["location"]["country"] == "US"

    def test_country_can_be_overridden(self):
        item = {"source_id": "c2", "name": "Canada Camp", "country": "CA"}
        result = normalize_scraped(item, "test")
        assert result["location"]["country"] == "CA"
