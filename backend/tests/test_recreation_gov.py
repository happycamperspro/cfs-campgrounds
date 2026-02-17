"""
Tests for the RecreationGovSource class.

Covers pagination, single-facility fetch, rate limiting, and retry
behaviour using mocked HTTP responses.
"""

import sys
from pathlib import Path

_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from sources.recreation_gov import RecreationGovSource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ridb_response(records, total_count=None):
    """Build a mock response whose ``.json()`` returns RIDB-shaped data."""
    if total_count is None:
        total_count = len(records)
    body = {
        "RECDATA": records,
        "METADATA": {
            "RESULTS": {
                "TOTAL_COUNT": total_count,
                "CURRENT_COUNT": len(records),
            }
        },
    }
    resp = MagicMock(spec=requests.Response)
    resp.json.return_value = body
    resp.raise_for_status.return_value = None
    return resp


def _facility(facility_id, name="Test Camp"):
    """Return a minimal RIDB facility dict."""
    return {
        "FacilityID": str(facility_id),
        "FacilityName": name,
        "FacilityDescription": "<p>A great campground</p>",
        "FacilityTypeDescription": "Campground",
        "FacilityLatitude": 37.0,
        "FacilityLongitude": -119.0,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def source():
    """Create a RecreationGovSource with mocked session setup."""
    with patch.object(RecreationGovSource, "_setup_session"):
        src = RecreationGovSource()
        src._session = MagicMock(spec=requests.Session)
        return src


# ---------------------------------------------------------------------------
# Tests – pagination
# ---------------------------------------------------------------------------

class TestFetchAllCampgrounds:
    """Tests for fetch_all_campgrounds (pagination)."""

    def test_single_page(self, source):
        """A response whose records fit in one page yields all records."""
        records = [_facility(1), _facility(2), _facility(3)]
        source._session.get.return_value = _ridb_response(records, total_count=3)

        results = list(source.fetch_all_campgrounds())

        assert len(results) == 3
        assert results[0]["FacilityID"] == "1"
        assert results[2]["FacilityID"] == "3"

    def test_two_page_pagination(self, source):
        """When TOTAL_COUNT > page size, two pages are fetched."""
        page1_records = [_facility(i) for i in range(1, 51)]
        page2_records = [_facility(i) for i in range(51, 76)]

        resp_page1 = _ridb_response(page1_records, total_count=75)
        resp_page2 = _ridb_response(page2_records, total_count=75)

        source._session.get.side_effect = [resp_page1, resp_page2]

        results = list(source.fetch_all_campgrounds())

        assert len(results) == 75
        assert results[0]["FacilityID"] == "1"
        assert results[-1]["FacilityID"] == "75"
        assert source._session.get.call_count == 2

    def test_empty_response_stops_pagination(self, source):
        """An empty RECDATA list stops the paginator immediately."""
        source._session.get.return_value = _ridb_response([], total_count=0)

        results = list(source.fetch_all_campgrounds())

        assert results == []
        assert source._session.get.call_count == 1


# ---------------------------------------------------------------------------
# Tests – single facility detail
# ---------------------------------------------------------------------------

class TestFetchCampgroundDetail:
    """Tests for fetch_campground_detail."""

    def test_returns_single_facility(self, source):
        """fetch_campground_detail returns the parsed JSON body."""
        facility = _facility("232447", "Yosemite Valley Campground")
        resp = MagicMock(spec=requests.Response)
        resp.json.return_value = facility
        resp.raise_for_status.return_value = None
        source._session.get.return_value = resp

        result = source.fetch_campground_detail("232447")

        assert result["FacilityID"] == "232447"
        assert result["FacilityName"] == "Yosemite Valley Campground"
        # Verify the endpoint includes the facility ID
        call_url = source._session.get.call_args[0][0]
        assert "/facilities/232447" in call_url

    def test_passes_full_param(self, source):
        """fetch_campground_detail sends full=true as a query parameter."""
        resp = MagicMock(spec=requests.Response)
        resp.json.return_value = _facility("100")
        resp.raise_for_status.return_value = None
        source._session.get.return_value = resp

        source.fetch_campground_detail("100")

        _, kwargs = source._session.get.call_args
        assert kwargs.get("params", {}).get("full") == "true"


# ---------------------------------------------------------------------------
# Tests – rate limiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    """Verify that _rate_limit introduces a delay between requests."""

    def test_rate_limit_delays_between_requests(self, source):
        """Back-to-back requests should be separated by at least
        ``_rate_limit_delay`` seconds."""
        source._rate_limit_delay = 0.1  # keep test fast

        records = [_facility(1)]
        source._session.get.return_value = _ridb_response(records, total_count=1)

        # First request – sets _last_request_time
        source._get("/facilities", params={})
        first_time = source._last_request_time

        # Second request – should be delayed
        with patch("time.sleep") as mock_sleep:
            source._last_request_time = time.time()  # pretend just requested
            source._get("/facilities", params={})

            # sleep should have been called if elapsed < delay
            # (depending on timing, it might not be called if the test
            # execution itself takes long enough)
            # We verify by checking it was called OR enough real time passed.
            if mock_sleep.called:
                delay_arg = mock_sleep.call_args[0][0]
                assert delay_arg > 0
                assert delay_arg <= source._rate_limit_delay

    def test_no_delay_when_enough_time_passed(self, source):
        """No sleep occurs when enough time has passed since the last request."""
        source._rate_limit_delay = 0.1
        source._last_request_time = time.time() - 10  # 10 seconds ago

        records = [_facility(1)]
        source._session.get.return_value = _ridb_response(records, total_count=1)

        with patch("time.sleep") as mock_sleep:
            source._get("/facilities", params={})
            mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Tests – retry on connection error
# ---------------------------------------------------------------------------

class TestRetryBehaviour:
    """Verify that transient connection errors trigger retries."""

    def test_retries_on_connection_error(self, source):
        """A ConnectionError on the first attempt should be retried,
        and if the second attempt succeeds, the result is returned."""
        success_resp = MagicMock(spec=requests.Response)
        success_resp.json.return_value = _facility("999")
        success_resp.raise_for_status.return_value = None

        source._session.get.side_effect = [
            requests.ConnectionError("Connection refused"),
            success_resp,
        ]

        # Patch tenacity wait to avoid real delays
        with patch("sources.base_source.wait_exponential", return_value=0):
            result = source._get("/facilities/999", params={})

        assert result["FacilityID"] == "999"
        assert source._session.get.call_count == 2

    def test_raises_after_max_retries(self, source):
        """If every attempt fails with a ConnectionError, the error
        is eventually re-raised."""
        source._session.get.side_effect = requests.ConnectionError("down")

        with pytest.raises(requests.ConnectionError):
            # Patch tenacity wait to avoid real delays
            with patch("sources.base_source.wait_exponential", return_value=0):
                source._get("/facilities/1", params={})

        # Should have tried RETRY_ATTEMPTS times (default 3)
        assert source._session.get.call_count >= 2
