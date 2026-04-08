"""Async API client for the Tracearr REST API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import aiohttp


class TracearrConnectionError(Exception):
    """Error to indicate a connection issue."""


class TracearrAuthenticationError(Exception):
    """Error to indicate an authentication issue."""


class TracearrError(Exception):
    """General Tracearr API error."""


@dataclass
class TracearrSessionData:
    """Represent a single active session/stream."""

    session_id: str = ""
    user: str = ""
    title: str = ""
    media_type: str = ""
    state: str = ""
    progress: int = 0
    quality: str = ""
    device: str = ""
    ip_address: str = ""
    location: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracearrSessionData:
        """Create from API response dict."""
        return cls(
            session_id=str(data.get("session_id", data.get("id", ""))),
            user=str(data.get("user", data.get("username", ""))),
            title=str(data.get("title", data.get("media_title", ""))),
            media_type=str(data.get("media_type", data.get("type", ""))),
            state=str(data.get("state", data.get("status", ""))),
            progress=int(data.get("progress", data.get("progress_percent", 0))),
            quality=str(data.get("quality", data.get("stream_quality", ""))),
            device=str(data.get("device", data.get("player", ""))),
            ip_address=str(data.get("ip_address", data.get("ip", ""))),
            location=str(data.get("location", "")),
        )


@dataclass
class TracearrActivity:
    """Represent current activity data."""

    stream_count: int = 0
    transcode_count: int = 0
    direct_play_count: int = 0
    direct_stream_count: int = 0
    total_bandwidth: int = 0
    lan_bandwidth: int = 0
    wan_bandwidth: int = 0
    sessions: list[TracearrSessionData] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracearrActivity:
        """Create from API response dict."""
        sessions_data = data.get("sessions", data.get("streams", []))
        sessions = [TracearrSessionData.from_dict(s) for s in sessions_data]
        return cls(
            stream_count=int(
                data.get("stream_count", data.get("total", len(sessions)))
            ),
            transcode_count=int(
                data.get("transcode_count", data.get("transcoding", 0))
            ),
            direct_play_count=int(
                data.get("direct_play_count", data.get("direct_play", 0))
            ),
            direct_stream_count=int(
                data.get("direct_stream_count", data.get("direct_stream", 0))
            ),
            total_bandwidth=int(
                data.get("total_bandwidth", data.get("bandwidth", 0))
            ),
            lan_bandwidth=int(data.get("lan_bandwidth", 0)),
            wan_bandwidth=int(data.get("wan_bandwidth", 0)),
            sessions=sessions,
        )


@dataclass
class TracearrUser:
    """Represent a Tracearr user."""

    user_id: str = ""
    username: str = ""
    trust_score: float = 0.0
    violations: int = 0
    is_active: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracearrUser:
        """Create from API response dict."""
        return cls(
            user_id=str(data.get("id", data.get("user_id", ""))),
            username=str(data.get("username", data.get("name", ""))),
            trust_score=float(data.get("trust_score", 0.0)),
            violations=int(data.get("violations", data.get("violation_count", 0))),
            is_active=bool(data.get("is_active", data.get("active", True))),
        )


@dataclass
class TracearrServer:
    """Represent a connected media server."""

    server_id: str = ""
    name: str = ""
    server_type: str = ""
    status: str = ""
    url: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracearrServer:
        """Create from API response dict."""
        return cls(
            server_id=str(data.get("id", data.get("server_id", ""))),
            name=str(data.get("name", "")),
            server_type=str(data.get("type", data.get("server_type", ""))),
            status=str(data.get("status", data.get("connection_status", ""))),
            url=str(data.get("url", "")),
        )


@dataclass
class TracearrLibrary:
    """Represent library statistics."""

    total_movies: int = 0
    total_shows: int = 0
    total_episodes: int = 0
    total_music: int = 0
    total_storage: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracearrLibrary:
        """Create from API response dict."""
        return cls(
            total_movies=int(data.get("total_movies", data.get("movies", 0))),
            total_shows=int(data.get("total_shows", data.get("shows", 0))),
            total_episodes=int(data.get("total_episodes", data.get("episodes", 0))),
            total_music=int(data.get("total_music", data.get("music", 0))),
            total_storage=float(data.get("total_storage", data.get("storage", 0.0))),
        )


@dataclass
class TracearrStatus:
    """Represent the Tracearr system status."""

    version: str = ""
    healthy: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracearrStatus:
        """Create from API response dict."""
        return cls(
            version=str(data.get("version", "")),
            healthy=bool(data.get("healthy", data.get("status", "") == "ok")),
        )


class TracearrClient:
    """Async API client for Tracearr."""

    def __init__(
        self,
        host: str,
        api_key: str,
        session: aiohttp.ClientSession,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the Tracearr API client."""
        self._host = host.rstrip("/")
        self._api_key = api_key
        self._session = session
        self._verify_ssl = verify_ssl

    @property
    def base_url(self) -> str:
        """Return the base URL."""
        return self._host

    async def _request(self, endpoint: str) -> dict[str, Any]:
        """Make an authenticated request to the Tracearr API."""
        url = f"{self._host}/api/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }
        ssl = None if self._verify_ssl else False
        try:
            async with self._session.get(
                url, headers=headers, ssl=ssl
            ) as response:
                if response.status == 401:
                    raise TracearrAuthenticationError("Invalid API key")
                if response.status == 403:
                    raise TracearrAuthenticationError("Forbidden")
                if response.status != 200:
                    raise TracearrError(
                        f"API request failed with status {response.status}"
                    )
                return await response.json()
        except TracearrAuthenticationError:
            raise
        except TracearrError:
            raise
        except aiohttp.ClientError as err:
            raise TracearrConnectionError(
                f"Error connecting to Tracearr: {err}"
            ) from err
        except Exception as err:
            raise TracearrConnectionError(
                f"Unexpected error connecting to Tracearr: {err}"
            ) from err

    async def async_get_status(self) -> TracearrStatus:
        """Get Tracearr system status."""
        data = await self._request("status")
        return TracearrStatus.from_dict(data)

    async def async_get_sessions(self) -> TracearrActivity:
        """Get current session/activity data."""
        data = await self._request("sessions")
        return TracearrActivity.from_dict(data)

    async def async_get_users(self) -> list[TracearrUser]:
        """Get all users."""
        data = await self._request("users")
        users_list = data if isinstance(data, list) else data.get("users", [])
        return [TracearrUser.from_dict(u) for u in users_list]

    async def async_get_servers(self) -> list[TracearrServer]:
        """Get connected media servers."""
        data = await self._request("servers")
        servers_list = data if isinstance(data, list) else data.get("servers", [])
        return [TracearrServer.from_dict(s) for s in servers_list]

    async def async_get_library(self) -> TracearrLibrary:
        """Get library statistics."""
        data = await self._request("library")
        return TracearrLibrary.from_dict(data)
