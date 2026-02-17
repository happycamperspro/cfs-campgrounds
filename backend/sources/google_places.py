"""
Google Places data source (stub).

This source will be implemented in Phase 2 to enrich campground records
with Google Places data (ratings, photos, place IDs, etc.).
"""

from typing import Any, Dict, Generator, Optional

from sources.base_source import BaseSource


class GooglePlacesSource(BaseSource):
    """Stub client for the Google Places API – not yet implemented."""

    @property
    def source_name(self) -> str:
        return "google_places"

    def _setup_session(self) -> None:
        pass

    def fetch_all_campgrounds(self) -> Generator[Dict[str, Any], None, None]:
        raise NotImplementedError(
            "GooglePlacesSource.fetch_all_campgrounds is not implemented"
        )

    def fetch_campground_detail(self, campground_id: str) -> Dict[str, Any]:
        raise NotImplementedError(
            "GooglePlacesSource.fetch_campground_detail is not implemented"
        )

    def search_place(
        self,
        name: str,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Search for a place by name and optional coordinates.

        Parameters
        ----------
        name:
            Human-readable name of the campground.
        lat:
            Latitude for location-biased search.
        lng:
            Longitude for location-biased search.

        Raises
        ------
        NotImplementedError
            Always -- this feature is planned for Phase 2.
        """
        raise NotImplementedError("Coming in Phase 2")
