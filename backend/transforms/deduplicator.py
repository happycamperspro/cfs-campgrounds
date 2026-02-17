"""
Cross-source deduplication for the campground data pipeline.

Identifies duplicate campground records across different sources by
combining geographic proximity with fuzzy name matching, then merges
them according to a configurable source-priority order.
"""
import copy
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from config.settings import DEDUP_DISTANCE_MILES, DEDUP_NAME_THRESHOLD
from transforms.geocoder import distance_miles

# Suffixes stripped before name comparison
_COMMON_SUFFIXES = re.compile(
    r"\b(campground|camping area|camp|cg|campsite|camping)\b",
    re.IGNORECASE,
)

# Default source priority (higher index = lower priority)
DEFAULT_PRIORITY: List[str] = [
    "nps",
    "recreation_gov",
    "koa",
    "hipcamp",
    "good_sam",
    "thousand_trails",
    "state_parks",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _name_similarity(a: str, b: str) -> float:
    """
    Compute similarity ratio between two campground names.

    Both names are lowercased and common campground suffixes are removed
    before the comparison so that e.g. "Yosemite Campground" and
    "Yosemite Camping Area" score higher.

    Returns
    -------
    float
        Similarity ratio in the range [0.0, 1.0].
    """
    if not a or not b:
        return 0.0

    def _clean(name: str) -> str:
        name = name.lower()
        name = _COMMON_SUFFIXES.sub("", name)
        # Collapse whitespace
        name = re.sub(r"\s+", " ", name).strip()
        return name

    return SequenceMatcher(None, _clean(a), _clean(b)).ratio()


def _merge_missing_fields(primary: Dict, secondary: Dict) -> Dict:
    """
    Fill empty / missing fields in *primary* from *secondary*.

    Merges nested sections (description, contact, details, amenities)
    and appends unique photos from the secondary record.

    Returns a **new** dict -- the originals are not mutated.
    """
    merged = copy.deepcopy(primary)

    # Top-level simple fields
    if not merged.get("description") and secondary.get("description"):
        merged["description"] = secondary["description"]

    # Contact
    pri_contact = merged.setdefault("contact", {})
    sec_contact = secondary.get("contact", {})
    for key in ("phone", "email", "reservationUrl"):
        if not pri_contact.get(key) and sec_contact.get(key):
            pri_contact[key] = sec_contact[key]

    # Details
    pri_details = merged.setdefault("details", {})
    sec_details = secondary.get("details", {})
    for key in ("totalSites", "season", "directions", "feesDescription", "adaAccess"):
        if not pri_details.get(key) and sec_details.get(key):
            pri_details[key] = sec_details[key]
    if not pri_details.get("siteTypes") and sec_details.get("siteTypes"):
        pri_details["siteTypes"] = sec_details["siteTypes"]

    # Amenities
    pri_amenities = merged.setdefault("amenities", {})
    sec_amenities = secondary.get("amenities", {})

    # Hookups -- prefer True from either source
    pri_hookups = pri_amenities.setdefault("hookups", {})
    sec_hookups = sec_amenities.get("hookups", {})
    for key in ("electric", "water", "sewer"):
        if sec_hookups.get(key) and not pri_hookups.get(key):
            pri_hookups[key] = True

    # Facilities list
    pri_facilities = set(pri_amenities.get("facilities", []))
    sec_facilities = set(sec_amenities.get("facilities", []))
    pri_amenities["facilities"] = sorted(pri_facilities | sec_facilities)

    # Activities list
    pri_activities = set(pri_amenities.get("activities", []))
    sec_activities = set(sec_amenities.get("activities", []))
    pri_amenities["activities"] = sorted(pri_activities | sec_activities)

    # Photos -- append unique URLs from secondary
    existing_urls = {p.get("url") for p in merged.get("photos", [])}
    for photo in secondary.get("photos", []):
        if photo.get("url") and photo["url"] not in existing_urls:
            merged.setdefault("photos", []).append(photo)
            existing_urls.add(photo["url"])

    # Location -- fill missing geo data
    pri_loc = merged.setdefault("location", {})
    sec_loc = secondary.get("location", {})
    if pri_loc.get("latitude") is None and sec_loc.get("latitude") is not None:
        pri_loc["latitude"] = sec_loc["latitude"]
        pri_loc["longitude"] = sec_loc["longitude"]
        pri_loc["geopoint"] = sec_loc.get("geopoint")

    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_duplicates(
    records: List[Dict],
) -> List[Tuple[int, int, float, float]]:
    """
    Identify probable duplicate pairs across different sources.

    Only cross-source pairs are considered (same-source pairs are skipped).
    Both records must have latitude and longitude.  A pair is flagged as a
    duplicate when:

    1. Geodesic distance <= ``DEDUP_DISTANCE_MILES`` (from config), **and**
    2. Fuzzy name similarity >= ``DEDUP_NAME_THRESHOLD`` (from config).

    Parameters
    ----------
    records : list[dict]
        Normalized campground records (must contain ``source``, ``name``,
        and ``location.latitude`` / ``location.longitude``).

    Returns
    -------
    list[tuple[int, int, float, float]]
        Each tuple is ``(index_a, index_b, name_score, distance_miles)``.
    """
    duplicates: List[Tuple[int, int, float, float]] = []

    for i in range(len(records)):
        rec_a = records[i]
        loc_a = rec_a.get("location", {})
        lat_a = loc_a.get("latitude")
        lng_a = loc_a.get("longitude")
        if lat_a is None or lng_a is None:
            continue

        for j in range(i + 1, len(records)):
            rec_b = records[j]

            # Skip same-source pairs
            if rec_a.get("source") == rec_b.get("source"):
                continue

            loc_b = rec_b.get("location", {})
            lat_b = loc_b.get("latitude")
            lng_b = loc_b.get("longitude")
            if lat_b is None or lng_b is None:
                continue

            dist = distance_miles(lat_a, lng_a, lat_b, lng_b)
            if dist > DEDUP_DISTANCE_MILES:
                continue

            score = _name_similarity(
                rec_a.get("name", ""), rec_b.get("name", "")
            )
            if score >= DEDUP_NAME_THRESHOLD:
                duplicates.append((i, j, score, dist))

    return duplicates


def resolve_duplicates(
    records: List[Dict],
    duplicates: List[Tuple[int, int, float, float]],
    priority: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Merge duplicate pairs, keeping the higher-priority source as primary.

    Parameters
    ----------
    records : list[dict]
        The full list of normalized records.
    duplicates : list[tuple]
        Output of :func:`find_duplicates`.
    priority : list[str], optional
        Source names ordered from highest to lowest priority.
        Defaults to :data:`DEFAULT_PRIORITY`.

    Returns
    -------
    list[dict]
        De-duplicated records with merged fields and cross-references
        stored in ``metadata.crossReferences``.
    """
    if priority is None:
        priority = DEFAULT_PRIORITY

    def _priority_rank(source: str) -> int:
        try:
            return priority.index(source)
        except ValueError:
            return len(priority)

    # Track which indices have been absorbed into another record
    absorbed: set = set()
    # Map primary index -> list of secondary indices merged into it
    merge_map: Dict[int, List[int]] = {}

    for idx_a, idx_b, _score, _dist in duplicates:
        if idx_a in absorbed or idx_b in absorbed:
            continue

        rec_a = records[idx_a]
        rec_b = records[idx_b]

        rank_a = _priority_rank(rec_a.get("source", ""))
        rank_b = _priority_rank(rec_b.get("source", ""))

        if rank_a <= rank_b:
            primary_idx, secondary_idx = idx_a, idx_b
        else:
            primary_idx, secondary_idx = idx_b, idx_a

        absorbed.add(secondary_idx)
        merge_map.setdefault(primary_idx, []).append(secondary_idx)

    # Build result list
    result: List[Dict] = []

    for idx, rec in enumerate(records):
        if idx in absorbed:
            continue

        if idx in merge_map:
            merged = copy.deepcopy(rec)
            cross_refs: List[Dict[str, str]] = []

            for sec_idx in merge_map[idx]:
                sec = records[sec_idx]
                merged = _merge_missing_fields(merged, sec)
                cross_refs.append({
                    "source": sec.get("source", ""),
                    "sourceId": sec.get("sourceId", ""),
                    "docId": sec.get("_doc_id", ""),
                })

            merged.setdefault("metadata", {})["crossReferences"] = cross_refs
            result.append(merged)
        else:
            result.append(copy.deepcopy(rec))

    return result
