"""
Geocoding utilities for the campground data pipeline.

Provides forward geocoding and distance calculation using geopy.
"""
from typing import Optional, Tuple

from geopy.distance import geodesic
from geopy.geocoders import Nominatim


def distance_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the geodesic distance in miles between two lat/lng points.

    Parameters
    ----------
    lat1, lng1 : float
        Coordinates of the first point.
    lat2, lng2 : float
        Coordinates of the second point.

    Returns
    -------
    float
        Distance in miles.
    """
    return geodesic((lat1, lng1), (lat2, lng2)).miles


def geocode_address(
    address: str,
    city: str,
    state: str,
    zip_code: str = "",
) -> Optional[Tuple[float, float]]:
    """
    Forward-geocode an address string via Nominatim.

    Constructs a query from the provided address components and
    returns the resulting (latitude, longitude) tuple, or ``None``
    if the lookup fails.

    Parameters
    ----------
    address : str
        Street address.
    city : str
        City name.
    state : str
        State name or abbreviation.
    zip_code : str, optional
        ZIP / postal code.

    Returns
    -------
    tuple[float, float] | None
        ``(latitude, longitude)`` on success, ``None`` on failure.
    """
    parts = [p for p in (address, city, state, zip_code) if p]
    if not parts:
        return None

    query = ", ".join(parts)

    geolocator = Nominatim(user_agent="campfire-campgrounds-pipeline/1.0")
    try:
        location = geolocator.geocode(query, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except Exception:
        pass

    return None


def is_within_radius(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
    radius_miles: float = 0.5,
) -> bool:
    """
    Check whether two points are within *radius_miles* of each other.

    Parameters
    ----------
    lat1, lng1 : float
        Coordinates of the first point.
    lat2, lng2 : float
        Coordinates of the second point.
    radius_miles : float
        Maximum allowed distance in miles (default 0.5).

    Returns
    -------
    bool
        ``True`` if the geodesic distance is at most *radius_miles*.
    """
    return distance_miles(lat1, lng1, lat2, lng2) <= radius_miles
