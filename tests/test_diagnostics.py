"""Tests for the Tracearr diagnostics platform."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.tracearr.api import (
    TracearrActivity,
    TracearrServer,
    TracearrStatus,
    TracearrUser,
)
from custom_components.tracearr.diagnostics import (
    TO_REDACT,
    async_get_config_entry_diagnostics,
)


class FakeCoordinator:
    """Fake coordinator for testing diagnostics."""

    def __init__(self, activity=None, users=None, servers=None, status=None):
        """Initialize with optional data."""
        self.activity = activity
        self.users = users
        self.servers = servers
        self.api_client = MagicMock()
        self.api_client.async_get_status = AsyncMock(
            return_value=status or TracearrStatus(version="1.5.0", healthy=True)
        )


class TestDiagnostics:
    """Tests for async_get_config_entry_diagnostics."""

    def test_api_key_in_redact_set(self):
        """Ensure the API key is in the redaction set."""
        assert "api_key" in TO_REDACT

    async def test_diagnostics_full_data(self):
        """Test diagnostics returns full data when all coordinator data is present."""
        activity = TracearrActivity(
            stream_count=3,
            transcode_count=1,
            direct_play_count=1,
            direct_stream_count=1,
            total_bandwidth=5000,
            sessions=[],
        )
        servers = [
            TracearrServer(
                server_id="s1",
                name="Plex",
                server_type="plex",
                status="connected",
                active_streams=2,
            ),
            TracearrServer(
                server_id="s2",
                name="Jellyfin",
                server_type="jellyfin",
                status="disconnected",
                active_streams=0,
            ),
        ]
        users = [
            TracearrUser(user_id="1", username="alice", trust_score=90.0, violations=0),
            TracearrUser(user_id="2", username="bob", trust_score=70.0, violations=2),
        ]
        status = TracearrStatus(version="2.0.0", healthy=True)

        coordinator = FakeCoordinator(
            activity=activity, users=users, servers=servers, status=status
        )
        entry = MagicMock()
        entry.runtime_data = coordinator
        entry.data = {
            "host": "http://tracearr.local:8080",
            "api_key": "trr_pub_secret123",
            "verify_ssl": True,
        }

        result = await async_get_config_entry_diagnostics(MagicMock(), entry)

        assert result["tracearr"]["version"] == "2.0.0"
        assert result["tracearr"]["healthy"] is True
        assert result["entry"]["host"] == "http://tracearr.local:8080"
        assert result["entry"]["api_key"] == "**REDACTED**"
        assert result["entry"]["verify_ssl"] is True
        assert len(result["servers"]) == 2
        assert result["servers"][0]["name"] == "Plex"
        assert result["servers"][0]["type"] == "plex"
        assert result["servers"][0]["status"] == "connected"
        assert result["servers"][0]["active_streams"] == 2
        assert result["servers"][1]["name"] == "Jellyfin"
        assert result["servers"][1]["status"] == "disconnected"
        assert result["activity"]["stream_count"] == 3
        assert result["activity"]["transcode_count"] == 1
        assert result["activity"]["total_bandwidth"] == 5000
        assert result["users"]["total"] == 2

    async def test_diagnostics_no_data(self):
        """Test diagnostics returns empty structures when no data is present."""
        coordinator = FakeCoordinator()
        entry = MagicMock()
        entry.runtime_data = coordinator
        entry.data = {
            "host": "http://tracearr.local:8080",
            "api_key": "trr_pub_secret123",
        }

        result = await async_get_config_entry_diagnostics(MagicMock(), entry)

        assert result["tracearr"]["version"] == "1.5.0"
        assert result["tracearr"]["healthy"] is True
        assert result["servers"] == []
        assert result["activity"] == {}
        assert result["users"]["total"] == 0

    async def test_diagnostics_servers_only(self):
        """Test diagnostics with server data but no activity or users."""
        servers = [
            TracearrServer(
                server_id="s1",
                name="Emby",
                server_type="emby",
                status="connected",
                active_streams=1,
            ),
        ]
        coordinator = FakeCoordinator(servers=servers)
        entry = MagicMock()
        entry.runtime_data = coordinator
        entry.data = {"host": "http://tracearr.local", "api_key": "key"}

        result = await async_get_config_entry_diagnostics(MagicMock(), entry)

        assert len(result["servers"]) == 1
        assert result["servers"][0]["name"] == "Emby"
        assert result["activity"] == {}
        assert result["users"]["total"] == 0
