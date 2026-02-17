"""
Recreation.gov (RIDB) data source.

Fetches campground facilities, campsites, media, and addresses from
the Recreation Information Database API.
"""

import logging
from typing import Any, Dict, Generator

from config import settings
from sources.base_source import BaseSource

logger = logging.getLogger(__name__)


class RecreationGovSource(BaseSource):
    """Client for the Recreation.gov RIDB API v1."""

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._page_size = settings.RIDB_PAGE_SIZE
        super().__init__(
            base_url=settings.RIDB_BASE_URL,
            rate_limit_delay=settings.RIDB_RATE_LIMIT_DELAY,
        )

    @property
    def source_name(self) -> str:
        return "recreation_gov"

    def _setup_session(self) -> None:
        self._session.headers.update(
            {
                "apikey": settings.RECREATION_GOV_API_KEY,
                "Accept": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Public fetch methods
    # ------------------------------------------------------------------

    def fetch_all_campgrounds(self) -> Generator[Dict[str, Any], None, None]:
        """Yield every camping facility from RIDB, fully expanded."""
        params: Dict[str, Any] = {
            "activity": "CAMPING",
            "full": "true",
            "limit": self._page_size,
        }
        yield from self._paginate(
            endpoint="/facilities",
            params=params,
            data_key="RECDATA",
            total_key_path=["METADATA", "RESULTS", "TOTAL_COUNT"],
        )

    def fetch_campground_detail(self, facility_id: str) -> Dict[str, Any]:
        """Return the full detail record for a single facility."""
        return self._get(f"/facilities/{facility_id}", params={"full": "true"})

    def fetch_campsites_for_facility(
        self, facility_id: str
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield every campsite belonging to *facility_id*."""
        params: Dict[str, Any] = {"limit": self._page_size}
        yield from self._paginate(
            endpoint=f"/facilities/{facility_id}/campsites",
            params=params,
            data_key="RECDATA",
            total_key_path=["METADATA", "RESULTS", "TOTAL_COUNT"],
        )

    def fetch_media_for_facility(
        self, facility_id: str
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield every media record belonging to *facility_id*."""
        params: Dict[str, Any] = {"limit": self._page_size}
        yield from self._paginate(
            endpoint=f"/facilities/{facility_id}/media",
            params=params,
            data_key="RECDATA",
            total_key_path=["METADATA", "RESULTS", "TOTAL_COUNT"],
        )

    def fetch_addresses_for_facility(
        self, facility_id: str
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield every address record belonging to *facility_id*."""
        params: Dict[str, Any] = {"limit": self._page_size}
        yield from self._paginate(
            endpoint=f"/facilities/{facility_id}/addresses",
            params=params,
            data_key="RECDATA",
            total_key_path=["METADATA", "RESULTS", "TOTAL_COUNT"],
        )
