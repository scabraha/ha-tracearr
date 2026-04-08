"""Tests for the Tracearr API client."""

import pytest
import aiohttp
from aioresponses import aioresponses

from custom_components.tracearr.api import (
    TracearrActivity,
    TracearrAuthenticationError,
    TracearrClient,
    TracearrConnectionError,
    TracearrError,
    TracearrLibrary,
    TracearrServer,
    TracearrSessionData,
    TracearrStatus,
    TracearrUser,
)


HOST = "http://tracearr.local:8080"
API_KEY = "test-api-key-123"


@pytest.fixture
def mock_aioresponse():
    """Provide aioresponses mock."""
    with aioresponses() as m:
        yield m


# --- Data model unit tests ---


class TestTracearrSessionData:
    """Tests for TracearrSessionData."""

    def test_from_dict_primary_keys(self):
        """Test creating session data from dict with primary keys."""
        data = {
            "session_id": "abc123",
            "user": "testuser",
            "title": "Movie Title",
            "media_type": "movie",
            "state": "playing",
            "progress": 50,
            "quality": "1080p",
            "device": "Chromecast",
            "ip_address": "192.168.1.10",
            "location": "Home",
        }
        session = TracearrSessionData.from_dict(data)
        assert session.session_id == "abc123"
        assert session.user == "testuser"
        assert session.title == "Movie Title"
        assert session.media_type == "movie"
        assert session.state == "playing"
        assert session.progress == 50
        assert session.quality == "1080p"
        assert session.device == "Chromecast"
        assert session.ip_address == "192.168.1.10"
        assert session.location == "Home"

    def test_from_dict_alternate_keys(self):
        """Test creating session data from dict with alternate key names."""
        data = {
            "id": "xyz789",
            "username": "altuser",
            "media_title": "TV Show",
            "type": "episode",
            "status": "paused",
            "progress_percent": 75,
            "stream_quality": "4K",
            "player": "AppleTV",
            "ip": "10.0.0.5",
        }
        session = TracearrSessionData.from_dict(data)
        assert session.session_id == "xyz789"
        assert session.user == "altuser"
        assert session.title == "TV Show"
        assert session.media_type == "episode"
        assert session.state == "paused"
        assert session.progress == 75
        assert session.quality == "4K"
        assert session.device == "AppleTV"
        assert session.ip_address == "10.0.0.5"

    def test_from_dict_defaults(self):
        """Test that missing keys default properly."""
        session = TracearrSessionData.from_dict({})
        assert session.session_id == ""
        assert session.user == ""
        assert session.title == ""
        assert session.progress == 0
        assert session.location == ""


class TestTracearrActivity:
    """Tests for TracearrActivity."""

    def test_from_dict_with_sessions(self):
        """Test creating activity from dict with sessions."""
        data = {
            "stream_count": 3,
            "transcode_count": 1,
            "direct_play_count": 2,
            "direct_stream_count": 0,
            "total_bandwidth": 5000,
            "lan_bandwidth": 3000,
            "wan_bandwidth": 2000,
            "sessions": [
                {"session_id": "1", "user": "user1", "title": "Movie 1"},
                {"session_id": "2", "user": "user2", "title": "Show 1"},
            ],
        }
        activity = TracearrActivity.from_dict(data)
        assert activity.stream_count == 3
        assert activity.transcode_count == 1
        assert activity.direct_play_count == 2
        assert activity.direct_stream_count == 0
        assert activity.total_bandwidth == 5000
        assert activity.lan_bandwidth == 3000
        assert activity.wan_bandwidth == 2000
        assert len(activity.sessions) == 2
        assert activity.sessions[0].user == "user1"

    def test_from_dict_alternate_keys(self):
        """Test using alternate key names."""
        data = {
            "total": 2,
            "transcoding": 1,
            "direct_play": 1,
            "direct_stream": 0,
            "bandwidth": 4000,
            "streams": [
                {"id": "1", "username": "u1"},
            ],
        }
        activity = TracearrActivity.from_dict(data)
        assert activity.stream_count == 2
        assert activity.transcode_count == 1
        assert activity.total_bandwidth == 4000
        assert len(activity.sessions) == 1

    def test_from_dict_empty(self):
        """Test defaults when no data provided."""
        activity = TracearrActivity.from_dict({})
        assert activity.stream_count == 0
        assert activity.sessions == []


class TestTracearrUser:
    """Tests for TracearrUser."""

    def test_from_dict(self):
        """Test creating user from dict."""
        data = {
            "id": "u1",
            "username": "john",
            "trust_score": 85.5,
            "violations": 2,
            "is_active": True,
        }
        user = TracearrUser.from_dict(data)
        assert user.user_id == "u1"
        assert user.username == "john"
        assert user.trust_score == 85.5
        assert user.violations == 2
        assert user.is_active is True

    def test_from_dict_alternate_keys(self):
        """Test using alternate key names."""
        data = {
            "user_id": "u2",
            "name": "jane",
            "violation_count": 0,
            "active": False,
        }
        user = TracearrUser.from_dict(data)
        assert user.user_id == "u2"
        assert user.username == "jane"
        assert user.violations == 0
        assert user.is_active is False


class TestTracearrServer:
    """Tests for TracearrServer."""

    def test_from_dict(self):
        """Test creating server from dict."""
        data = {
            "id": "s1",
            "name": "My Plex",
            "type": "plex",
            "status": "connected",
            "url": "http://plex.local:32400",
        }
        server = TracearrServer.from_dict(data)
        assert server.server_id == "s1"
        assert server.name == "My Plex"
        assert server.server_type == "plex"
        assert server.status == "connected"
        assert server.url == "http://plex.local:32400"


class TestTracearrLibrary:
    """Tests for TracearrLibrary."""

    def test_from_dict(self):
        """Test creating library from dict."""
        data = {
            "total_movies": 500,
            "total_shows": 100,
            "total_episodes": 5000,
            "total_music": 200,
            "total_storage": 2048.5,
        }
        library = TracearrLibrary.from_dict(data)
        assert library.total_movies == 500
        assert library.total_shows == 100
        assert library.total_episodes == 5000
        assert library.total_music == 200
        assert library.total_storage == 2048.5

    def test_from_dict_alternate_keys(self):
        """Test using alternate key names."""
        data = {"movies": 50, "shows": 10, "episodes": 500}
        library = TracearrLibrary.from_dict(data)
        assert library.total_movies == 50
        assert library.total_shows == 10
        assert library.total_episodes == 500


class TestTracearrStatus:
    """Tests for TracearrStatus."""

    def test_from_dict(self):
        """Test creating status from dict."""
        data = {"version": "1.2.3", "healthy": True}
        status = TracearrStatus.from_dict(data)
        assert status.version == "1.2.3"
        assert status.healthy is True

    def test_from_dict_status_ok(self):
        """Test healthy flag from status field."""
        data = {"version": "1.0.0", "status": "ok"}
        status = TracearrStatus.from_dict(data)
        assert status.healthy is True

    def test_from_dict_status_not_ok(self):
        """Test healthy flag when status is not ok."""
        data = {"version": "1.0.0", "status": "error"}
        status = TracearrStatus.from_dict(data)
        assert status.healthy is False


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
        """Test getting system status."""
        mock_aioresponse.get(
            f"{HOST}/api/status",
            payload={"version": "2.0.0", "healthy": True},
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            status = await client.async_get_status()
        assert status.version == "2.0.0"
        assert status.healthy is True

    async def test_get_sessions(self, mock_aioresponse):
        """Test getting session/activity data."""
        mock_aioresponse.get(
            f"{HOST}/api/sessions",
            payload={
                "stream_count": 2,
                "transcode_count": 1,
                "direct_play_count": 1,
                "direct_stream_count": 0,
                "total_bandwidth": 3000,
                "lan_bandwidth": 2000,
                "wan_bandwidth": 1000,
                "sessions": [
                    {"session_id": "s1", "user": "alice", "title": "Movie"},
                    {"session_id": "s2", "user": "bob", "title": "Show"},
                ],
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

    async def test_get_users(self, mock_aioresponse):
        """Test getting users."""
        mock_aioresponse.get(
            f"{HOST}/api/users",
            payload=[
                {"id": "1", "username": "alice", "trust_score": 90.0, "violations": 0},
                {"id": "2", "username": "bob", "trust_score": 70.0, "violations": 3},
            ],
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            users = await client.async_get_users()
        assert len(users) == 2
        assert users[0].username == "alice"
        assert users[1].violations == 3

    async def test_get_users_nested(self, mock_aioresponse):
        """Test getting users from nested response."""
        mock_aioresponse.get(
            f"{HOST}/api/users",
            payload={
                "users": [
                    {"id": "1", "username": "carol"},
                ]
            },
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            users = await client.async_get_users()
        assert len(users) == 1
        assert users[0].username == "carol"

    async def test_get_servers(self, mock_aioresponse):
        """Test getting servers."""
        mock_aioresponse.get(
            f"{HOST}/api/servers",
            payload=[
                {
                    "id": "s1",
                    "name": "Plex",
                    "type": "plex",
                    "status": "connected",
                    "url": "http://plex:32400",
                },
            ],
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            servers = await client.async_get_servers()
        assert len(servers) == 1
        assert servers[0].name == "Plex"
        assert servers[0].status == "connected"

    async def test_get_library(self, mock_aioresponse):
        """Test getting library stats."""
        mock_aioresponse.get(
            f"{HOST}/api/library",
            payload={
                "total_movies": 1000,
                "total_shows": 200,
                "total_episodes": 10000,
                "total_music": 500,
                "total_storage": 4096.0,
            },
        )
        async with aiohttp.ClientSession() as session:
            client = TracearrClient(
                host=HOST, api_key=API_KEY, session=session, verify_ssl=False
            )
            library = await client.async_get_library()
        assert library.total_movies == 1000
        assert library.total_shows == 200

    async def test_authentication_error(self, mock_aioresponse):
        """Test authentication error on 401."""
        mock_aioresponse.get(
            f"{HOST}/api/status",
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
            f"{HOST}/api/status",
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
            f"{HOST}/api/status",
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
            f"{HOST}/api/status",
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
