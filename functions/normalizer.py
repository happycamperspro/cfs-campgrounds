"""
Normalizer for campground data from NPS and Recreation.gov APIs.

Maps API responses into the unified Firestore document schema.
"""
import re
import unicodedata
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Optional

from google.cloud.firestore_v1 import GeoPoint

from regions import get_region, get_state_full_name, normalize_state


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def generate_slug(name: str, state: str, city: str = "") -> str:
    if not name:
        return ""
    parts = [name, city, state] if city else [name, state]
    raw = "-".join(p for p in parts if p)
    raw = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    raw = raw.lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw)
    raw = raw.strip("-")
    return raw


def strip_html(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = unescape(cleaned)
    return cleaned.strip()


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _find_address(addresses: List[Dict], addr_type: str = "Physical") -> Optional[Dict]:
    if not addresses:
        return None
    for addr in addresses:
        if addr.get("FacilityAddressType") == addr_type:
            return addr
    return addresses[0] if addresses else None


def _find_nps_address(addresses: List[Dict], addr_type: str = "Physical") -> Optional[Dict]:
    if not addresses:
        return None
    for addr in addresses:
        if addr.get("type") == addr_type:
            return addr
    return addresses[0] if addresses else None


def _summarize_campsites(campsites: Optional[List[Dict]]) -> Dict:
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
    if not amenities:
        return []
    skip_values = {"", "no", "none"}
    extracted: List[str] = []
    for key, value in amenities.items():
        str_val = str(value).strip().lower()
        if str_val in skip_values:
            continue
        label = re.sub(r"([a-z])([A-Z])", r"\1 \2", key)
        label = label.replace("_", " ").title()
        extracted.append(label)
    return extracted


# ---------------------------------------------------------------------------
# Main normalizer functions
# ---------------------------------------------------------------------------

def normalize_recreation_gov(facility: Dict, campsites: Optional[List[Dict]] = None) -> Dict:
    now = datetime.now(timezone.utc)
    facility_id = str(facility.get("FacilityID", ""))

    address_rec = _find_address(facility.get("FACILITYADDRESS", []))
    street = (address_rec or {}).get("FacilityStreetAddress1", "")
    city = (address_rec or {}).get("City", "")
    raw_state = (address_rec or {}).get("AddressStateCode", "")
    zip_code = (address_rec or {}).get("PostalCode", "")

    state_code = normalize_state(raw_state)
    state_full = get_state_full_name(state_code)
    region = get_region(state_code)

    lat = _safe_float(facility.get("FacilityLatitude"))
    lng = _safe_float(facility.get("FacilityLongitude"))
    geopoint = GeoPoint(lat, lng) if lat is not None and lng is not None else None

    activities = [
        a.get("ActivityName", "")
        for a in facility.get("ACTIVITY", [])
        if a.get("ActivityName")
    ]

    photos = []
    for media in facility.get("MEDIA", [])[:10]:
        url = media.get("URL", "")
        if url:
            entry = {"url": url}
            title = media.get("Title", "")
            if title:
                entry["caption"] = title
            photos.append(entry)

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
            "feesDescription": strip_html(facility.get("FacilityUseFeeDescription", "")),
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
    now = datetime.now(timezone.utc)
    cg_id = str(campground.get("id", ""))

    address_rec = _find_nps_address(campground.get("addresses", []))
    street = (address_rec or {}).get("line1", "")
    city = (address_rec or {}).get("city", "")
    raw_state = (address_rec or {}).get("stateCode", "")
    zip_code = (address_rec or {}).get("postalCode", "")

    state_code = normalize_state(raw_state)
    state_full = get_state_full_name(state_code)
    region = get_region(state_code)

    lat = _safe_float(campground.get("latitude"))
    lng = _safe_float(campground.get("longitude"))
    geopoint = GeoPoint(lat, lng) if lat is not None and lng is not None else None

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

    fees_list = campground.get("fees", [])
    fees_desc = "; ".join(
        f"{f.get('title', '')}: ${f.get('cost', '')}"
        for f in fees_list
        if f.get("cost")
    )

    hours_list = campground.get("operatingHours", [])
    season = ""
    if hours_list:
        season = hours_list[0].get("description", "")

    contacts_raw = campground.get("contacts", {})
    phone = ""
    email = ""
    phone_numbers = contacts_raw.get("phoneNumbers", [])
    if phone_numbers:
        phone = phone_numbers[0].get("phoneNumber", "")
    email_addresses = contacts_raw.get("emailAddresses", [])
    if email_addresses:
        email = email_addresses[0].get("emailAddress", "")

    amenities_raw = campground.get("amenities", {})
    amenity_names = _extract_nps_amenities(amenities_raw)

    reservation_url = campground.get("reservationUrl", "") or campground.get("url", "")

    photos = []
    for img in campground.get("images", [])[:10]:
        url = img.get("url", "")
        if url:
            photos.append({"url": url, "caption": img.get("title", "")})

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
            "adaAccess": campground.get("accessibility", {}).get("adaInfo", ""),
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
