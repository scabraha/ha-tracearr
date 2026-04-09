"""Async API client for the Tracearr REST API.

Targets the Tracearr public API (v1) documented at /api-docs.
All endpoints live under /api/v1/public/ and require a Bearer token
with the ``trr_pub_`` prefix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import aiohttp

API_PATH_PREFIX = "api/v1/public"


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracearrSessionData:
        """Create from a Tracearr public API stream object."""
        # Compute progress percentage from millisecond values when available.
        progress_ms = int(data.get("progressMs", 0))
        duration_ms = int(data.get("durationMs", 0))
        if duration_ms > 0:
            progress_pct = round(progress_ms * 100 / duration_ms)
        else:
            progress_pct = int(data.get("progress", 0))

        return cls(
            session_id=str(data.get("id", "")),
            user=str(data.get("username", "")),
            title=str(data.get("mediaTitle", "")),
            media_type=str(data.get("mediaType", "")),
            state=str(data.get("state", "")),
            progress=progress_pct,
            quality=str(data.get("resolution", "")),
            device=str(data.get("device", "")),
        )


@dataclass
class TracearrActivity:
    """Represent current activity data."""

    stream_count: int = 0
    transcode_count: int = 0
    direct_play_count: int = 0
    direct_stream_count: int = 0
    total_bandwidth: int = 0
    sessions: list[TracearrSessionData] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracearrActivity:
        """Create from the Tracearr ``GET /streams`` response.

        Expected shape::

            {
              "data": [ … stream objects … ],
              "summary": {
                "total": 5,
                "transcodes": 1,
                "directStreams": 1,
                "directPlays": 3,
                "totalBitrate": "50.2 Mbps",
                "byServer": [ … ]
              }
            }
        """
        sessions_data = data.get("data", [])
        sessions = [TracearrSessionData.from_dict(s) for s in sessions_data]

        summary = data.get("summary", {})

        # Compute total bandwidth (kbps) from individual stream bitrates.
        total_bw = sum(int(s.get("bitrate", 0)) for s in sessions_data)

        return cls(
            stream_count=int(summary.get("total", len(sessions))),
            transcode_count=int(summary.get("transcodes", 0)),
            direct_play_count=int(summary.get("directPlays", 0)),
            direct_stream_count=int(summary.get("directStreams", 0)),
            total_bandwidth=total_bw,
            sessions=sessions,
        )


@dataclass
class TracearrUser:
    """Represent a Tracearr user."""

    user_id: str = ""
    username: str = ""
    trust_score: float = 0.0
    violations: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracearrUser:
        """Create from a Tracearr public API user object."""
        return cls(
            user_id=str(data.get("id", "")),
            username=str(data.get("displayName", data.get("username", ""))),
            trust_score=float(data.get("trustScore", 0.0)),
            violations=int(data.get("totalViolations", 0)),
        )


@dataclass
class TracearrServer:
    """Represent a connected media server.

    Populated from the ``servers`` array in the ``GET /health`` response.
    """

    server_id: str = ""
    name: str = ""
    server_type: str = ""
    status: str = ""
    active_streams: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracearrServer:
        """Create from a server entry in the /health response."""
        online = data.get("online", False)
        return cls(
            server_id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            server_type=str(data.get("type", "")),
            status="connected" if online else "disconnected",
            active_streams=int(data.get("activeStreams", 0)),
        )


@dataclass
class TracearrStatus:
    """Represent the Tracearr system status."""

    version: str = ""
    healthy: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracearrStatus:
        """Create from the Tracearr ``GET /health`` response."""
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
        url = f"{self._host}/{API_PATH_PREFIX}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }
        ssl = None if self._verify_ssl else False
        try:
            async with self._session.get(url, headers=headers, ssl=ssl) as response:
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
        """Get Tracearr system status via ``GET /health``."""
        data = await self._request("health")
        return TracearrStatus.from_dict(data)

    async def async_get_sessions(self) -> TracearrActivity:
        """Get current session/activity data via ``GET /streams``."""
        data = await self._request("streams")
        return TracearrActivity.from_dict(data)

    async def async_get_users(self) -> list[TracearrUser]:
        """Get all users via ``GET /users``."""
        data = await self._request("users")
        users_list = data.get("data", [])
        return [TracearrUser.from_dict(u) for u in users_list]

    async def async_get_servers(self) -> list[TracearrServer]:
        """Get connected media servers from ``GET /health``.

        The public API does not have a dedicated ``/servers`` endpoint;
        server information is embedded in the ``/health`` response.
        """
        data = await self._request("health")
        servers_list = data.get("servers", [])
        return [TracearrServer.from_dict(s) for s in servers_list]
