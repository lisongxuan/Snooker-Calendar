"""
Unit tests for Snooker Calendar API (app.py)

Supports two execution modes:

  1. Mock mode (default) — no database or running server needed:
       cd backend && python -m pytest test_app.py -v

  2. Live mode — test against a real running server:
       cd backend && python -m pytest test_app.py -v --base-url http://localhost:8000

     Or via environment variable:
       TEST_BASE_URL=http://localhost:8000 python -m pytest test_app.py -v

Covers:
  - GET /api/players          (pagination, search, caching, error handling)
  - GET /api/calendar/{id}    (file download, generation, 404, errors)
  - GET /api/info/lastupdated (normal, caching, error handling)
  - CORS middleware
  - Edge cases
"""
import os
import sys
from unittest.mock import patch, MagicMock
from time import time as _time

import pytest
import httpx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _is_live_mode(request) -> bool:
    return bool(
        request.config.getoption("--base-url", default=None)
        or os.environ.get("TEST_BASE_URL")
    )


@pytest.fixture()
def client(request):
    """HTTP client: TestClient in mock mode, httpx.Client in live mode."""
    if _is_live_mode(request):
        url = (
            request.config.getoption("--base-url")
            or os.environ.get("TEST_BASE_URL", "")
        ).rstrip("/")
        with httpx.Client(base_url=url, timeout=15.0) as c:
            yield c
    else:
        from fastapi.testclient import TestClient
        from app import app
        yield TestClient(app)


@pytest.fixture(autouse=True)
def _clear_caches(request):
    """Reset in-memory caches between tests (mock mode only)."""
    if _is_live_mode(request):
        yield
        return
    import app as _app
    _app._players_cache.clear()
    _app._last_updated_cache["data"] = None
    _app._last_updated_cache["ts"] = 0
    yield
    _app._players_cache.clear()
    _app._last_updated_cache["data"] = None
    _app._last_updated_cache["ts"] = 0


def _skip_in_live(request):
    """Call at start of mock-only tests to skip when running against live URL."""
    if _is_live_mode(request):
        pytest.skip("Test only runs in mock mode (requires patching internals)")


# ---------------------------------------------------------------------------
# Sample data factories (mock mode)
# ---------------------------------------------------------------------------

def _make_player(position=1, player_id=1, first="Ronnie", last="O'Sullivan",
                 nationality="England"):
    return {
        "type": 1,
        "firstname": first,
        "lastname": last,
        "surname_first": False,
        "nationality": nationality,
        "born": "1975-12-05",
        "num_ranking_titles": 7,
        "position": position,
        "player_id": player_id,
        "sum_value": 1200000.0,
        "last_updated": "2025-06-01T00:00:00",
    }


def _make_players(n=5):
    return [_make_player(position=i, player_id=i, first=f"Player{i}", last=f"Last{i}")
            for i in range(1, n + 1)]


# ===========================================================================
# GET /api/players — works in BOTH modes
# ===========================================================================

class TestGetPlayersLive:
    """Tests that validate real API behaviour (work in both mock & live)."""

    def test_default_returns_200(self, client):
        resp = client.get("/api/players")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_pagination_returns_200(self, client):
        resp = client.get("/api/players?page=1&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_search_returns_200(self, client):
        resp = client.get("/api/players?search=Ronnie")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_combined_params_returns_200(self, client):
        resp = client.get("/api/players?page=1&limit=10&search=Trump")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_large_page_returns_empty_or_list(self, client):
        resp = client.get("/api/players?page=99999&limit=50")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_player_fields_structure(self, client):
        """Verify response items contain expected fields."""
        resp = client.get("/api/players?page=1&limit=1")
        assert resp.status_code == 200
        data = resp.json()
        if data:
            expected = {"firstname", "lastname", "nationality", "position", "player_id", "sum_value"}
            assert expected.issubset(data[0].keys()), f"Missing: {expected - data[0].keys()}"

    def test_search_result_relevance(self, client, is_live):
        """Live: verify search for a known player returns relevant results."""
        if not is_live:
            pytest.skip("Relevance check only meaningful against live data")
        resp = client.get("/api/players?search=O'Sullivan")
        data = resp.json()
        if data:
            names = [f"{p.get('firstname', '')} {p.get('lastname', '')}".lower() for p in data]
            assert any("sullivan" in n for n in names)


# ===========================================================================
# GET /api/players — mock-only (caching & error injection)
# ===========================================================================

class TestGetPlayersMock:

    def test_params_forwarded(self, request, client):
        _skip_in_live(request)
        with patch("app.query_all_ranking_players") as mock_query:
            mock_query.return_value = _make_players(3)
            client.get("/api/players")
            mock_query.assert_called_once_with(page=1, limit=50, search=None)

    def test_search_forwarded(self, request, client):
        _skip_in_live(request)
        with patch("app.query_all_ranking_players") as mock_query:
            mock_query.return_value = [_make_player(first="Judd", last="Trump")]
            resp = client.get("/api/players?search=Judd")
            assert resp.json()[0]["firstname"] == "Judd"
            mock_query.assert_called_once_with(page=1, limit=50, search="Judd")

    def test_empty_result(self, request, client):
        _skip_in_live(request)
        with patch("app.query_all_ranking_players", return_value=[]):
            resp = client.get("/api/players")
            assert resp.status_code == 200
            assert resp.json() == []

    def test_none_result(self, request, client):
        _skip_in_live(request)
        with patch("app.query_all_ranking_players", return_value=None):
            resp = client.get("/api/players")
            assert resp.status_code == 200

    def test_cache_hit(self, request, client):
        _skip_in_live(request)
        with patch("app.query_all_ranking_players") as mock_query:
            mock_query.return_value = _make_players(2)
            resp1 = client.get("/api/players?page=1&limit=50")
            resp2 = client.get("/api/players?page=1&limit=50")
            assert resp1.json() == resp2.json()
            assert mock_query.call_count == 1

    def test_cache_miss_different_params(self, request, client):
        _skip_in_live(request)
        with patch("app.query_all_ranking_players") as mock_query:
            mock_query.return_value = _make_players(2)
            client.get("/api/players?page=1&limit=50")
            client.get("/api/players?page=2&limit=50")
            assert mock_query.call_count == 2

    def test_cache_expiry(self, request, client):
        _skip_in_live(request)
        with patch("app._time") as mock_time, \
             patch("app.query_all_ranking_players") as mock_query:
            t0 = 1000000.0
            mock_time.return_value = t0
            mock_query.return_value = _make_players(1)
            client.get("/api/players")
            assert mock_query.call_count == 1
            mock_time.return_value = t0 + 301
            client.get("/api/players")
            assert mock_query.call_count == 2

    def test_query_exception_returns_500(self, request, client):
        _skip_in_live(request)
        with patch("app.query_all_ranking_players", side_effect=RuntimeError("DB connection lost")):
            resp = client.get("/api/players")
            assert resp.status_code == 500
            assert "DB connection lost" in resp.json()["detail"]


# ===========================================================================
# GET /api/calendar/{player_id} — works in BOTH modes
# ===========================================================================

class TestCalendarLive:

    def test_invalid_player_id_type(self, client):
        """Non-integer player_id → 422."""
        resp = client.get("/api/calendar/abc")
        assert resp.status_code == 422

    def test_known_player_calendar(self, client, is_live):
        """Live: download calendar for a real player."""
        if not is_live:
            pytest.skip("Needs live data")
        resp = client.get("/api/calendar/1")
        if resp.status_code == 200:
            assert "VCALENDAR" in resp.text
            ct = resp.headers.get("content-type", "")
            assert "calendar" in ct or "text" in ct
        else:
            assert resp.status_code in (404, 500)

    def test_nonexistent_player_calendar(self, client, is_live):
        """Live: bogus player_id returns 404 or 500."""
        if not is_live:
            pytest.skip("Needs live server")
        resp = client.get("/api/calendar/9999999")
        assert resp.status_code in (200, 404, 500)

    def test_calendar_content_type(self, client, is_live):
        """Live: Content-Type should be text/calendar on success."""
        if not is_live:
            pytest.skip("Needs live server")
        resp = client.get("/api/calendar/1")
        if resp.status_code == 200:
            assert "calendar" in resp.headers.get("content-type", "")


# ===========================================================================
# GET /api/calendar/{player_id} — mock-only
# ===========================================================================

class TestCalendarMock:

    def test_file_served_via_route(self, request, client):
        _skip_in_live(request)
        dummy = os.path.join("ics_calendars", "1.ics")
        os.makedirs("ics_calendars", exist_ok=True)
        try:
            with open(dummy, "wb") as f:
                f.write(b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n")
            resp = client.get("/api/calendar/1")
            assert resp.status_code == 200
            assert "VCALENDAR" in resp.text
        finally:
            if os.path.exists(dummy):
                os.remove(dummy)

    def test_no_matches_404(self, request, client):
        _skip_in_live(request)
        with patch("app.os.path.exists", return_value=False), \
             patch.dict("sys.modules", {"player_matches_to_ics": MagicMock()}), \
             patch("app.get_current_season", return_value=2025):
            sys.modules["player_matches_to_ics"].generate_player_calendar = MagicMock(return_value=None)
            resp = client.get("/api/calendar/9999")
            assert resp.status_code in (404, 500)

    def test_calendar_negative_id(self, request, client):
        _skip_in_live(request)
        with patch("app.os.path.exists", return_value=False), \
             patch.dict("sys.modules", {"player_matches_to_ics": MagicMock()}), \
             patch("app.get_current_season", return_value=2025):
            sys.modules["player_matches_to_ics"].generate_player_calendar = MagicMock(return_value=None)
            resp = client.get("/api/calendar/-1")
            assert resp.status_code in (404, 500)


# ===========================================================================
# GET /api/info/lastupdated — works in BOTH modes
# ===========================================================================

class TestLastUpdatedLive:

    def test_returns_200(self, client):
        resp = client.get("/api/info/lastupdated")
        assert resp.status_code == 200

    def test_response_is_list(self, client, is_live):
        """Live: response should be a list of info records."""
        if not is_live:
            pytest.skip("Schema assertion meaningful against live data")
        resp = client.get("/api/info/lastupdated")
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "info" in data[0] or "lastupdated" in data[0]


# ===========================================================================
# GET /api/info/lastupdated — mock-only
# ===========================================================================

class TestLastUpdatedMock:

    def test_normal_response(self, request, client):
        _skip_in_live(request)
        with patch("app.query_info_last_updated") as mock_query:
            mock_query.return_value = [
                {"info": "matches", "lastupdated": "2025-06-01T12:00:00"},
                {"info": "rankings", "lastupdated": "2025-05-28T08:00:00"},
            ]
            resp = client.get("/api/info/lastupdated")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["info"] == "matches"

    def test_cache_hit(self, request, client):
        _skip_in_live(request)
        with patch("app.query_info_last_updated") as mock_query:
            mock_query.return_value = [{"info": "x", "lastupdated": "2025-01-01"}]
            client.get("/api/info/lastupdated")
            client.get("/api/info/lastupdated")
            assert mock_query.call_count == 1

    def test_cache_expiry(self, request, client):
        _skip_in_live(request)
        with patch("app._time") as mock_time, \
             patch("app.query_info_last_updated") as mock_query:
            t0 = 1000000.0
            mock_time.return_value = t0
            mock_query.return_value = [{"info": "old"}]
            client.get("/api/info/lastupdated")
            assert mock_query.call_count == 1
            mock_time.return_value = t0 + 61
            mock_query.return_value = [{"info": "new"}]
            resp = client.get("/api/info/lastupdated")
            assert mock_query.call_count == 2
            assert resp.json()[0]["info"] == "new"

    def test_none_not_cached(self, request, client):
        _skip_in_live(request)
        with patch("app.query_info_last_updated", return_value=None) as mock_query:
            client.get("/api/info/lastupdated")
            client.get("/api/info/lastupdated")
            assert mock_query.call_count == 2

    def test_query_exception_returns_500(self, request, client):
        _skip_in_live(request)
        with patch("app.query_info_last_updated", side_effect=RuntimeError("timeout")):
            resp = client.get("/api/info/lastupdated")
            assert resp.status_code == 500
            assert "timeout" in resp.json()["detail"]


# ===========================================================================
# CORS — works in BOTH modes
# ===========================================================================

class TestCORS:

    def test_unknown_origin_no_cors_header(self, client):
        resp = client.get(
            "/api/players",
            headers={"Origin": "https://evil.example.com"},
        )
        assert resp.headers.get("access-control-allow-origin") is None

    def test_cors_headers_for_allowed_origin(self, client, is_live, base_url):
        if is_live:
            origin = base_url or "http://localhost"
        else:
            import app as _app
            if not _app.allowed_origins:
                pytest.skip("No CORS origins configured in config.txt")
            origin = _app.allowed_origins[0]
        resp = client.get("/api/players", headers={"Origin": origin})
        acao = resp.headers.get("access-control-allow-origin")
        if not is_live:
            assert acao == origin


# ===========================================================================
# Edge cases & smoke — works in BOTH modes
# ===========================================================================

class TestEdgeCases:

    def test_nonexistent_route_returns_404(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code in (404, 405)

    def test_negative_page(self, client, is_live):
        if not is_live:
            with patch("app.query_all_ranking_players", return_value=[]):
                resp = client.get("/api/players?page=-1&limit=10")
                assert resp.status_code == 200
        else:
            resp = client.get("/api/players?page=-1&limit=10")
            assert resp.status_code in (200, 422, 500)

    def test_zero_limit(self, client, is_live):
        if not is_live:
            with patch("app.query_all_ranking_players", return_value=[]):
                resp = client.get("/api/players?page=1&limit=0")
                assert resp.status_code == 200
        else:
            resp = client.get("/api/players?page=1&limit=0")
            assert resp.status_code in (200, 422, 500)

    def test_api_root_not_found(self, client):
        resp = client.get("/api/")
        assert resp.status_code in (404, 405, 307)

    def test_health_smoke(self, client):
        """At least one endpoint is alive and responds."""
        resp = client.get("/api/players?page=1&limit=1")
        assert resp.status_code == 200
