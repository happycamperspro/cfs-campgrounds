"""
Abstract base class for all campground data sources.

Provides session management, rate limiting, retries with exponential
backoff, and a generic paginator.  Concrete subclasses implement the
fetch methods for a specific government API.
"""

import abc
import logging
import time
from typing import Any, Dict, Generator, Optional, Sequence

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings

logger = logging.getLogger(__name__)


class BaseSource(abc.ABC):
    """Base class every data-source adapter must extend."""

    # ------------------------------------------------------------------
    # Construction / session
    # ------------------------------------------------------------------

    def __init__(
        self,
        base_url: str,
        rate_limit_delay: float = 0.5,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._rate_limit_delay = rate_limit_delay
        self._last_request_time: float = 0.0
        self._session = requests.Session()
        self._setup_session()

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Return a short, unique slug that identifies this source."""

    @abc.abstractmethod
    def _setup_session(self) -> None:
        """Configure session headers / auth.  Called once during __init__."""

    @abc.abstractmethod
    def fetch_all_campgrounds(self) -> Generator[Dict[str, Any], None, None]:
        """Yield every campground record from this source."""

    @abc.abstractmethod
    def fetch_campground_detail(self, campground_id: str) -> Dict[str, Any]:
        """Return the full detail record for a single campground."""

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _rate_limit(self) -> None:
        """Block until at least ``_rate_limit_delay`` seconds have elapsed
        since the last request."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
        stop=stop_after_attempt(settings.RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=settings.RETRY_BACKOFF_BASE,
            min=2,
            max=8,
        ),
        reraise=True,
    )
    def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Rate-limited GET request with automatic retries.

        Parameters
        ----------
        endpoint:
            Path appended to ``_base_url`` (e.g. ``/facilities``).
        params:
            Optional query-string parameters.

        Returns
        -------
        Parsed JSON body of the response.
        """
        self._rate_limit()
        url = f"{self._base_url}{endpoint}"
        logger.debug("GET %s  params=%s", url, params)
        response = self._session.get(url, params=params)
        self._last_request_time = time.time()
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def _paginate(
        self,
        endpoint: str,
        params: Dict[str, Any],
        data_key: str,
        total_key_path: Sequence[str],
    ) -> Generator[Dict[str, Any], None, None]:
        """Generic offset-based paginator.

        Parameters
        ----------
        endpoint:
            API path (e.g. ``/facilities``).
        params:
            Base query-string parameters. ``offset`` and ``limit`` will be
            added / overwritten automatically.
        data_key:
            Top-level key in the response that contains the list of records.
        total_key_path:
            Sequence of keys to traverse to reach the total-count value
            (e.g. ``["METADATA", "RESULTS", "TOTAL_COUNT"]``).

        Yields
        ------
        Individual records from each page.
        """
        offset = 0
        limit = params.get("limit", 50)
        total: Optional[int] = None

        while True:
            page_params = {**params, "offset": offset, "limit": limit}
            data = self._get(endpoint, page_params)

            # Resolve total count on first page.
            if total is None:
                total = data
                for key in total_key_path:
                    total = total[key]
                total = int(total)
                logger.info(
                    "%s: paginating %s – %d total records",
                    self.source_name,
                    endpoint,
                    total,
                )

            records = data.get(data_key, [])
            if not records:
                break

            yield from records

            offset += limit
            if offset >= total:
                break
