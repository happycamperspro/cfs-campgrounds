"""
Normalizer module for the campground data pipeline.

Maps different API/scraper formats (Recreation.gov RIDB, NPS, Scrapy items)
into a unified Firestore document schema.
"""
import re
import unicodedata
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Optional

from google.cloud.firestore_v1 import GeoPoint

from config.regions import get_region, get_state_full_name, normalize_state


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def generate_slug(name: str, state: str, city: str = "") -> str:
    """
    Generate a URL-safe slug from a campground name and location.

    Normalizes unicode characters, lowercases, and replaces
    non-alphanumeric characters with hyphens.
    """
    if not name:
        return ""

    parts = [name, city, state] if city else [name, state]
    raw = "-".join(p for p in parts if p)

    # Normalize unicode to ASCII-compatible form
    raw = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    raw = raw.lower()
    # Replace any non-alphanumeric character with a hyphen
    raw = re.sub(r"[^a-z0-9]+", "-", raw)
    # Strip leading/trailing hyphens
    raw = raw.strip("-")
    return raw


def strip_html(text: str) -> str:
    """
    Remove HTML tags from *text* and unescape HTML entities.

    Returns an empty string for None / empty input.
    """
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = unescape(cleaned)
    return cleaned.strip()


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert *value* to float; return None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _find_address(
    addresses: List[Dict], addr_type: str = "Physical"
) -> Optional[Dict]:
    """Find an RIDB address record whose FacilityAddressType matches *addr_type*."""
    if not addresses:
        return None
    for addr in addresses:
        if addr.get("FacilityAddressType") == addr_type:
            return addr
    # Fallback: return the first address if no exact match
    return addresses[0] if addresses else None


def _find_nps_address(
    addresses: List[Dict], addr_type: str = "Physical"
) -> Optional[Dict]:
    """Find an NPS address record whose type matches *addr_type*."""
    if not addresses:
        return None
    for addr in addresses:
        if addr.get("type") == addr_type:
            return addr
    return addresses[0] if addresses else None


def _summarize_campsites(campsites: Optional[List[Dict]]) -> Dict:
    """
    Summarize RIDB campsite records.

    Returns a dict with total count, a mapping of site type counts,
    and boolean flags for hookup availability (electric, water, sewer)
    derived from the ATTRIBUTES list on each campsite.
    """
    result: Dict[str, Any] = {
        "totalSites": 0,
        "siteTypes": {},
        "hasElectricHookup": False,
        "hasWaterHookup": False,
        "hasSewerHookup": False,
    }
    if not campsites:
        return result

    result["totalSites"] = len(campsites)

    for site in campsites:
        site_type = site.get("CampsiteType", "Standard")
        result["siteTypes"][site_type] = result["siteTypes"].get(site_type, 0) + 1

        for attr in site.get("ATTRIBUTES", []):
            attr_name = (attr.get("AttributeName", "") or "").lower()
            attr_val = (attr.get("AttributeValue", "") or "").lower()
            if attr_val in ("", "no", "none", "n/a"):
                continue
            if "electric" in attr_name and "hookup" in attr_name:
                result["hasElectricHookup"] = True
            if "water" in attr_name and "hookup" in attr_name:
                result["hasWaterHookup"] = True
            if "sewer" in attr_name and "hookup" in attr_name:
                result["hasSewerHookup"] = True

    return result


def _extract_nps_amenities(amenities: Dict) -> List[str]:
    """
    Extract amenity names from NPS key-value pairs.

    Skips entries whose value is empty, "no", or "none" (case-insensitive).
    Converts camelCase/PascalCase keys to readable labels.
    """
    if not amenities:
        return []

    skip_values = {"", "no", "none"}
    extracted: List[str] = []

    for key, value in amenities.items():
        str_val = str(value).strip().lower()
        if str_val in skip_values:
            continue
        # Convert camelCase key to readable label
        label = re.sub(r"([a-z])([A-Z])", r"\1 \2", key)
        label = label.replace("_", " ").title()
        extracted.append(label)

    return extracted


# ---------------------------------------------------------------------------
# Main normalizer functions
# ---------------------------------------------------------------------------

def normalize_recreation_gov(
    facility: Dict, campsites: Optional[List[Dict]] = None
) -> Dict:
    """
    Normalize a Recreation.gov RIDB facility into the unified Firestore schema.

    Parameters
    ----------
    facility : dict
        Raw facility dict from the RIDB API.
    campsites : list[dict], optional
        Associated campsite records from RIDB.

    Returns
    -------
    dict
        Normalized document with ``_doc_id`` set to ``recreation_gov_{FacilityID}``.
    """
    now = datetime.now(timezone.utc)
    facility_id = str(facility.get("FacilityID", ""))

    # Address
    address_rec = _find_address(facility.get("FACILITYADDRESS", []))
    street = (address_rec or {}).get("FacilityStreetAddress1", "")
    city = (address_rec or {}).get("City", "")
    raw_state = (address_rec or {}).get("AddressStateCode", "")
    zip_code = (address_rec or {}).get("PostalCode", "")

    state_code = normalize_state(raw_state)
    state_full = get_state_full_name(state_code)
    region = get_region(state_code)

    # Geo
    lat = _safe_float(facility.get("FacilityLatitude"))
    lng = _safe_float(facility.get("FacilityLongitude"))
    geopoint = GeoPoint(lat, lng) if lat is not None and lng is not None else None

    # Activities
    activities = [
        a.get("ActivityName", "")
        for a in facility.get("ACTIVITY", [])
        if a.get("ActivityName")
    ]

    # Photos (cap at 10)
    photos = []
    for media in facility.get("MEDIA", [])[:10]:
        photo_entry: Dict[str, str] = {}
        url = media.get("URL", "")
        if url:
            photo_entry["url"] = url
        title = media.get("Title", "")
        if title:
            photo_entry["caption"] = title
        if photo_entry.get("url"):
            photos.append(photo_entry)

    # Campsites summary
    cs = _summarize_campsites(campsites)

    name = facility.get("FacilityName", "")
    description = strip_html(facility.get("FacilityDescription", ""))

    return {
        "_doc_id": f"recreation_gov_{facility_id}",
        "name": name,
        "slug": generate_slug(name, state_code, city),
        "description": description,
        "source": "recreation_gov",
        "sourceId": facility_id,
        "location": {
            "address": street,
            "city": city,
            "state": state_code,
            "stateFullName": state_full,
            "zip": zip_code,
            "country": "US",
            "geopoint": geopoint,
            "latitude": lat,
            "longitude": lng,
            "region": region,
        },
        "contact": {
            "phone": facility.get("FacilityPhone", ""),
            "email": facility.get("FacilityEmail", ""),
            "reservationUrl": (
                f"https://www.recreation.gov/camping/campgrounds/{facility_id}"
                if facility_id
                else ""
            ),
        },
        "details": {
            "totalSites": cs["totalSites"],
            "siteTypes": cs["siteTypes"],
            "season": "",
            "reservable": facility.get("Reservable", False),
            "facilityType": facility.get("FacilityTypeDescription", ""),
            "directions": strip_html(facility.get("FacilityDirections", "")),
            "feesDescription": strip_html(
                facility.get("FacilityUseFeeDescription", "")
            ),
            "adaAccess": facility.get("FacilityAdaAccess", ""),
        },
        "amenities": {
            "hookups": {
                "electric": cs["hasElectricHookup"],
                "water": cs["hasWaterHookup"],
                "sewer": cs["hasSewerHookup"],
            },
            "facilities": [],
            "activities": activities,
        },
        "photos": photos,
        "ratings": {
            "avgRating": 0,
            "totalReviews": 0,
        },
        "metadata": {
            "createdAt": now,
            "updatedAt": now,
            "lastSyncedAt": now,
            "sourceLastUpdated": facility.get("LastUpdatedDate", ""),
            "isActive": True,
            "isVerified": True,
            "syncSource": "pipeline_v1",
        },
    }


def normalize_nps(campground: Dict) -> Dict:
    """
    Normalize an NPS campground record into the unified Firestore schema.

    Parameters
    ----------
    campground : dict
        Raw campground dict from the NPS API.

    Returns
    -------
    dict
        Normalized document with ``_doc_id`` set to ``nps_{id}``.
    """
    now = datetime.now(timezone.utc)
    cg_id = str(campground.get("id", ""))

    # Address
    address_rec = _find_nps_address(campground.get("addresses", []))
    street = (address_rec or {}).get("line1", "")
    city = (address_rec or {}).get("city", "")
    raw_state = (address_rec or {}).get("stateCode", "")
    zip_code = (address_rec or {}).get("postalCode", "")

    state_code = normalize_state(raw_state)
    state_full = get_state_full_name(state_code)
    region = get_region(state_code)

    # Geo
    lat = _safe_float(campground.get("latitude"))
    lng = _safe_float(campground.get("longitude"))
    geopoint = GeoPoint(lat, lng) if lat is not None and lng is not None else None

    # Campsites (NPS nested object)
    nps_campsites = campground.get("campsites", {})
    total_sites_raw = nps_campsites.get("totalSites", 0)
    total_sites = int(total_sites_raw) if total_sites_raw else 0

    site_types: Dict[str, int] = {}
    for key in ("tentOnly", "electricalHookups", "rvOnly", "walkBoatTo",
                "group", "horse", "other"):
        count_raw = nps_campsites.get(key, 0)
        count = int(count_raw) if count_raw else 0
        if count > 0:
            site_types[key] = count

    has_electric = int(nps_campsites.get("electricalHookups", 0) or 0) > 0

    # Fees
    fees_list = campground.get("fees", [])
    fees_desc = "; ".join(
        f"{f.get('title', '')}: ${f.get('cost', '')}"
        for f in fees_list
        if f.get("cost")
    )

    # Operating hours
    hours_list = campground.get("operatingHours", [])
    season = ""
    if hours_list:
        first_hours = hours_list[0]
        season = first_hours.get("description", "")

    # Contacts
    contacts_raw = campground.get("contacts", {})
    phone = ""
    email = ""
    phone_numbers = contacts_raw.get("phoneNumbers", [])
    if phone_numbers:
        phone = phone_numbers[0].get("phoneNumber", "")
    email_addresses = contacts_raw.get("emailAddresses", [])
    if email_addresses:
        email = email_addresses[0].get("emailAddress", "")

    # Amenities
    amenities_raw = campground.get("amenities", {})
    amenity_names = _extract_nps_amenities(amenities_raw)

    # Reservation URL
    reservation_url = campground.get("reservationUrl", "") or campground.get("url", "")

    # Photos (cap at 10)
    photos = []
    for img in campground.get("images", [])[:10]:
        url = img.get("url", "")
        if url:
            photos.append({
                "url": url,
                "caption": img.get("title", ""),
            })

    name = campground.get("name", "")
    description = strip_html(campground.get("description", ""))
    directions = strip_html(campground.get("directionsOverview", ""))

    return {
        "_doc_id": f"nps_{cg_id}",
        "name": name,
        "slug": generate_slug(name, state_code, city),
        "description": description,
        "source": "nps",
        "sourceId": cg_id,
        "location": {
            "address": street,
            "city": city,
            "state": state_code,
            "stateFullName": state_full,
            "zip": zip_code,
            "country": "US",
            "geopoint": geopoint,
            "latitude": lat,
            "longitude": lng,
            "region": region,
        },
        "contact": {
            "phone": phone,
            "email": email,
            "reservationUrl": reservation_url,
        },
        "details": {
            "totalSites": total_sites,
            "siteTypes": site_types,
            "season": season,
            "reservable": bool(campground.get("reservationUrl")),
            "facilityType": "Campground",
            "directions": directions,
            "feesDescription": fees_desc,
            "adaAccess": campground.get("accessibility", {}).get(
                "adaInfo", ""
            ),
        },
        "amenities": {
            "hookups": {
                "electric": has_electric,
                "water": False,
                "sewer": False,
            },
            "facilities": amenity_names,
            "activities": [],
        },
        "photos": photos,
        "ratings": {
            "avgRating": 0,
            "totalReviews": 0,
        },
        "metadata": {
            "createdAt": now,
            "updatedAt": now,
            "lastSyncedAt": now,
            "sourceLastUpdated": campground.get("lastIndexedDate", ""),
            "isActive": True,
            "isVerified": True,
            "syncSource": "pipeline_v1",
        },
    }


def normalize_scraped(item: Dict, source_name: str) -> Dict:
    """
    Normalize a Scrapy item (or similar dict) into the unified Firestore schema.

    This is a generic normalizer that maps common field names and
    handles missing fields gracefully with sensible defaults.

    Parameters
    ----------
    item : dict
        Scraped data with keys like ``name``, ``source_id``, ``latitude``, etc.
    source_name : str
        Identifier for the scraper source (e.g. ``"koa"``, ``"hipcamp"``).

    Returns
    -------
    dict
        Normalized document with ``_doc_id`` set to ``{source_name}_{source_id}``.
    """
    now = datetime.now(timezone.utc)
    source_id = str(item.get("source_id", ""))

    raw_state = item.get("state", "")
    state_code = normalize_state(raw_state)
    state_full = get_state_full_name(state_code)
    region = get_region(state_code)
    city = item.get("city", "")

    lat = _safe_float(item.get("latitude"))
    lng = _safe_float(item.get("longitude"))
    geopoint = GeoPoint(lat, lng) if lat is not None and lng is not None else None

    name = item.get("name", "")
    description = strip_html(item.get("description", ""))

    # Photos
    raw_photos = item.get("photos", []) or []
    photos = []
    for p in raw_photos[:10]:
        if isinstance(p, str):
            photos.append({"url": p, "caption": ""})
        elif isinstance(p, dict) and p.get("url"):
            photos.append({"url": p["url"], "caption": p.get("caption", "")})

    # Amenities
    raw_amenities = item.get("amenities", []) or []
    if isinstance(raw_amenities, dict):
        amenity_list = list(raw_amenities.keys())
    elif isinstance(raw_amenities, list):
        amenity_list = [str(a) for a in raw_amenities]
    else:
        amenity_list = []

    activities = item.get("activities", []) or []

    # Hookups
    hookups = item.get("hookups", {}) or {}

    # Site info
    total_sites = item.get("total_sites", 0)
    try:
        total_sites = int(total_sites) if total_sites else 0
    except (ValueError, TypeError):
        total_sites = 0

    site_types = item.get("site_types", {}) or {}

    return {
        "_doc_id": f"{source_name}_{source_id}",
        "name": name,
        "slug": generate_slug(name, state_code, city),
        "description": description,
        "source": source_name,
        "sourceId": source_id,
        "location": {
            "address": item.get("address", ""),
            "city": city,
            "state": state_code,
            "stateFullName": state_full,
            "zip": item.get("zip", ""),
            "country": item.get("country", "US"),
            "geopoint": geopoint,
            "latitude": lat,
            "longitude": lng,
            "region": region,
        },
        "contact": {
            "phone": item.get("phone", ""),
            "email": item.get("email", ""),
            "reservationUrl": item.get("reservation_url", ""),
        },
        "details": {
            "totalSites": total_sites,
            "siteTypes": site_types,
            "season": item.get("season", ""),
            "reservable": bool(item.get("reservable", False)),
            "facilityType": item.get("facility_type", "Campground"),
            "directions": item.get("directions", ""),
            "feesDescription": item.get("fees_description", ""),
            "adaAccess": item.get("ada_access", ""),
        },
        "amenities": {
            "hookups": {
                "electric": bool(hookups.get("electric", False)),
                "water": bool(hookups.get("water", False)),
                "sewer": bool(hookups.get("sewer", False)),
            },
            "facilities": amenity_list,
            "activities": activities,
        },
        "photos": photos,
        "ratings": {
            "avgRating": item.get("avg_rating", 0) or 0,
            "totalReviews": item.get("total_reviews", 0) or 0,
        },
        "metadata": {
            "createdAt": now,
            "updatedAt": now,
            "lastSyncedAt": now,
            "sourceLastUpdated": item.get("last_updated", ""),
            "isActive": True,
            "isVerified": True,
            "syncSource": "pipeline_v1",
        },
    }
