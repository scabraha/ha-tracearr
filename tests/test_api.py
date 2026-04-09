"""Tests for the Tracearr API client."""

import pytest
import aiohttp
from aioresponses import aioresponses

from custom_components.tracearr.api import (
    API_PATH_PREFIX,
    TracearrActivity,
    TracearrAuthenticationError,
    TracearrClient,
    TracearrConnectionError,
    TracearrError,
    TracearrServer,
    TracearrSessionData,
    TracearrStatus,
    TracearrUser,
)


HOST = "http://tracearr.local:8080"
API_KEY = "trr_pub_test-key-123"
BASE = f"{HOST}/{API_PATH_PREFIX}"


@pytest.fixture
def mock_aioresponse():
    """Provide aioresponses mock."""
    with aioresponses() as m:
        yield m


# --- Data model unit tests ---


class TestTracearrSessionData:
    """Tests for TracearrSessionData."""

    def test_from_dict_public_api_keys(self):
        """Test creating session data from the public API stream object."""
        data = {
            "id": "abc123",
            "username": "testuser",
            "mediaTitle": "Movie Title",
            "mediaType": "movie",
            "state": "playing",
            "progressMs": 3600000,
            "durationMs": 7200000,
            "resolution": "1080p",
            "device": "Chromecast",
        }
        session = TracearrSessionData.from_dict(data)
        assert session.session_id == "abc123"
        assert session.user == "testuser"
        assert session.title == "Movie Title"
        assert session.media_type == "movie"
        assert session.state == "playing"
        assert session.progress == 50  # 3600000/7200000 * 100
        assert session.quality == "1080p"
        assert session.device == "Chromecast"

    def test_from_dict_progress_zero_duration(self):
        """Test progress when duration is zero."""
        data = {"id": "s1", "progressMs": 5000, "durationMs": 0}
        session = TracearrSessionData.from_dict(data)
        assert session.progress == 0

    def test_from_dict_defaults(self):
        """Test that missing keys default properly."""
        session = TracearrSessionData.from_dict({})
        assert session.session_id == ""
        assert session.user == ""
        assert session.title == ""
        assert session.progress == 0


class TestTracearrActivity:
    """Tests for TracearrActivity."""

    def test_from_dict_with_streams_response(self):
        """Test creating activity from the /streams response shape."""
        data = {
            "data": [
                {
                    "id": "s1",
                    "username": "alice",
                    "mediaTitle": "Movie 1",
                    "mediaType": "movie",
                    "state": "playing",
                    "bitrate": 3000,
                },
                {
                    "id": "s2",
                    "username": "bob",
                    "mediaTitle": "Show 1",
                    "mediaType": "episode",
                    "state": "playing",
                    "bitrate": 2000,
                },
            ],
            "summary": {
                "total": 2,
                "transcodes": 1,
                "directPlays": 1,
                "directStreams": 0,
                "totalBitrate": "5.0 Mbps",
            },
        }
        activity = TracearrActivity.from_dict(data)
        assert activity.stream_count == 2
        assert activity.transcode_count == 1
        assert activity.direct_play_count == 1
        assert activity.direct_stream_count == 0
        assert activity.total_bandwidth == 5000  # sum of bitrates
        assert len(activity.sessions) == 2
        assert activity.sessions[0].user == "alice"

    def test_from_dict_empty(self):
        """Test defaults when no data provided."""
        activity = TracearrActivity.from_dict({})
        assert activity.stream_count == 0
        assert activity.sessions == []
        assert activity.total_bandwidth == 0


class TestTracearrUser:
    """Tests for TracearrUser."""

    def test_from_dict(self):
        """Test creating user from public API user object."""
        data = {
            "id": "u1",
            "username": "john",
            "displayName": "John Smith",
            "trustScore": 85.5,
            "totalViolations": 2,
        }
        user = TracearrUser.from_dict(data)
        assert user.user_id == "u1"
        assert user.username == "John Smith"
        assert user.trust_score == 85.5
        assert user.violations == 2

    def test_from_dict_fallback_to_username(self):
        """Test falling back to username when displayName is missing."""
        data = {
            "id": "u2",
            "username": "jane",
            "trustScore": 0.0,
            "totalViolations": 0,
        }
        user = TracearrUser.from_dict(data)
        assert user.username == "jane"

    def test_from_dict_defaults(self):
        """Test defaults for empty dict."""
        user = TracearrUser.from_dict({})
        assert user.user_id == ""
        assert user.username == ""
        assert user.trust_score == 0.0
        assert user.violations == 0


class TestTracearrServer:
    """Tests for TracearrServer."""

    def test_from_dict_online(self):
        """Test creating server from /health server entry (online)."""
        data = {
            "id": "s1",
            "name": "My Plex",
            "type": "plex",
            "online": True,
            "activeStreams": 3,
        }
        server = TracearrServer.from_dict(data)
        assert server.server_id == "s1"
        assert server.name == "My Plex"
        assert server.server_type == "plex"
        assert server.status == "connected"
        assert server.active_streams == 3

    def test_from_dict_offline(self):
        """Test creating server when offline."""
        data = {
            "id": "s2",
            "name": "Jellyfin",
            "type": "jellyfin",
            "online": False,
            "activeStreams": 0,
        }
        server = TracearrServer.from_dict(data)
        assert server.status == "disconnected"
        assert server.active_streams == 0


class TestTracearrStatus:
    """Tests for TracearrStatus."""

    def test_from_dict_status_ok(self):
        """Test healthy flag from /health status field."""
        data = {"version": "1.5.0", "status": "ok"}
        status = TracearrStatus.from_dict(data)
        assert status.version == "1.5.0"
        assert status.healthy is True

    def test_from_dict_status_not_ok(self):
        """Test healthy flag when status is not ok."""
        data = {"version": "1.5.0", "status": "degraded"}
        status = TracearrStatus.from_dict(data)
        assert status.healthy is False

    def test_from_dict_healthy_explicit(self):
        """Test explicit healthy flag."""
        data = {"version": "2.0.0", "healthy": True}
        status = TracearrStatus.from_dict(data)
        assert status.healthy is True


# --- API client tests ---


class TestTracearrClient:
    """Tests for TracearrClient."""

    async def test_base_url(self):
        """Test base_url property."""
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host="http://tracearr.local:8080/",
                api_key="key",
                session=session,
            )
            assert client.base_url == "http://tracearr.local:8080"

    async def test_get_status(self, mock_aioresponse):
        """Test getting system status via /health."""
        mock_aioresponse.get(
            f"{BASE}/health",
            payload={
                "status": "ok",
                "version": "1.5.0",
                "timestamp": "2026-01-01T00:00:00Z",
                "servers": [],
            },
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            status = await client.async_get_status()
        assert status.version == "1.5.0"
        assert status.healthy is True

    async def test_get_sessions(self, mock_aioresponse):
        """Test getting session/activity data via /streams."""
        mock_aioresponse.get(
            f"{BASE}/streams",
            payload={
                "data": [
                    {
                        "id": "s1",
                        "username": "alice",
                        "mediaTitle": "Movie",
                        "mediaType": "movie",
                        "state": "playing",
                        "bitrate": 2000,
                    },
                    {
                        "id": "s2",
                        "username": "bob",
                        "mediaTitle": "Show",
                        "mediaType": "episode",
                        "state": "playing",
                        "bitrate": 1500,
                    },
                ],
                "summary": {
                    "total": 2,
                    "transcodes": 1,
                    "directPlays": 1,
                    "directStreams": 0,
                    "totalBitrate": "3.5 Mbps",
                },
            },
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            activity = await client.async_get_sessions()
        assert activity.stream_count == 2
        assert activity.transcode_count == 1
        assert len(activity.sessions) == 2
        assert activity.sessions[0].user == "alice"
        assert activity.total_bandwidth == 3500

    async def test_get_users(self, mock_aioresponse):
        """Test getting users via /users (paginated response)."""
        mock_aioresponse.get(
            f"{BASE}/users",
            payload={
                "data": [
                    {
                        "id": "1",
                        "username": "alice",
                        "displayName": "Alice",
                        "trustScore": 90.0,
                        "totalViolations": 0,
                    },
                    {
                        "id": "2",
                        "username": "bob",
                        "displayName": "Bob",
                        "trustScore": 70.0,
                        "totalViolations": 3,
                    },
                ],
                "meta": {"total": 2, "page": 1, "pageSize": 25},
            },
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            users = await client.async_get_users()
        assert len(users) == 2
        assert users[0].username == "Alice"
        assert users[1].violations == 3

    async def test_get_servers(self, mock_aioresponse):
        """Test getting servers from /health response."""
        mock_aioresponse.get(
            f"{BASE}/health",
            payload={
                "status": "ok",
                "version": "1.5.0",
                "timestamp": "2026-01-01T00:00:00Z",
                "servers": [
                    {
                        "id": "s1",
                        "name": "Plex",
                        "type": "plex",
                        "online": True,
                        "activeStreams": 2,
                    },
                ],
            },
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            servers = await client.async_get_servers()
        assert len(servers) == 1
        assert servers[0].name == "Plex"
        assert servers[0].status == "connected"
        assert servers[0].active_streams == 2

    async def test_authentication_error(self, mock_aioresponse):
        """Test authentication error on 401."""
        mock_aioresponse.get(
            f"{BASE}/health",
            status=401,
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            with pytest.raises(TracearrAuthenticationError):
                await client.async_get_status()

    async def test_forbidden_error(self, mock_aioresponse):
        """Test authentication error on 403."""
        mock_aioresponse.get(
            f"{BASE}/health",
            status=403,
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            with pytest.raises(TracearrAuthenticationError):
                await client.async_get_status()

    async def test_server_error(self, mock_aioresponse):
        """Test general error on 500."""
        mock_aioresponse.get(
            f"{BASE}/health",
            status=500,
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            with pytest.raises(TracearrError):
                await client.async_get_status()

    async def test_connection_error(self, mock_aioresponse):
        """Test connection error."""
        mock_aioresponse.get(
            f"{BASE}/health",
            exception=aiohttp.ClientError("Connection refused"),
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            with pytest.raises(TracearrConnectionError):
                await client.async_get_status()

    async def test_trailing_slash_stripped(self):
        """Test that trailing slash on host is stripped."""
        async with aiohttp.ClientSession() as session:
            c = TracearrClient(
                host="http://example.com/",
                api_key="key",
                session=session,
            )
            assert c.base_url == "http://example.com"
