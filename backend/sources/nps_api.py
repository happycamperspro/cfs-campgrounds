"""
National Park Service (NPS) data source.

Fetches campground and park data from the NPS Developer API.
NPS uses ``start`` / ``limit`` pagination rather than ``offset``, so
this source overrides pagination with a custom implementation.
"""

import logging
from typing import Any, Dict, Generator, Optional

from config import settings
from sources.base_source import BaseSource

logger = logging.getLogger(__name__)


class NPSSource(BaseSource):
    """Client for the NPS Developer API v1."""

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._page_size = settings.NPS_PAGE_SIZE
        super().__init__(
            base_url=settings.NPS_BASE_URL,
            rate_limit_delay=settings.NPS_RATE_LIMIT_DELAY,
        )

    @property
    def source_name(self) -> str:
        return "nps"

    def _setup_session(self) -> None:
        self._session.headers.update(
            {
                "X-Api-Key": settings.NPS_API_KEY,
                "Accept": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Custom NPS pagination
    # ------------------------------------------------------------------

    def _paginate_nps(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """NPS-specific paginator using ``start`` / ``limit`` params.

        The NPS API returns ``data`` (list of records) and ``total``
        (string representing the total count) in each response.
        """
        params = dict(params or {})
        start = 0
        total: Optional[int] = None

        while True:
            page_params = {**params, "start": start, "limit": self._page_size}
            response = self._get(endpoint, page_params)

            if total is None:
                total = int(response["total"])
                logger.info(
                    "%s: paginating %s – %d total records",
                    self.source_name,
                    endpoint,
                    total,
                )

            records = response.get("data", [])
            if not records:
                break

            yield from records

            start += self._page_size
            if start >= total:
                break

    # ------------------------------------------------------------------
    # Public fetch methods
    # ------------------------------------------------------------------

    def fetch_all_campgrounds(self) -> Generator[Dict[str, Any], None, None]:
        """Yield every campground record from the NPS API."""
        yield from self._paginate_nps("/campgrounds")

    def fetch_campground_detail(self, campground_id: str) -> Dict[str, Any]:
        """Return the detail record for a single NPS campground.

        The NPS API does not support a ``/campgrounds/{id}`` path; instead
        we filter by the ``id`` query parameter and return the first match.
        """
        response = self._get("/campgrounds", params={"id": campground_id})
        data = response.get("data", [])
        if not data:
            raise LookupError(
                f"NPS campground not found: {campground_id}"
            )
        return data[0]

    def fetch_park_info(self, park_code: str) -> Dict[str, Any]:
        """Return park-level information for a given *park_code*.

        Returns the first matching park record.
        """
        response = self._get("/parks", params={"parkCode": park_code})
        data = response.get("data", [])
        if not data:
            raise LookupError(f"NPS park not found: {park_code}")
        return data[0]
