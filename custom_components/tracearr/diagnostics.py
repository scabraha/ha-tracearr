"""Diagnostics support for the Tracearr integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .coordinator import TracearrConfigEntry

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: TracearrConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    status = await coordinator.api_client.async_get_status()

    servers_data: list[dict[str, Any]] = []
    if coordinator.servers:
        servers_data = [
            {
                "name": server.name,
                "type": server.server_type,
                "status": server.status,
                "active_streams": server.active_streams,
            }
            for server in coordinator.servers
        ]

    activity_data: dict[str, Any] = {}
    if coordinator.activity:
        activity_data = {
            "stream_count": coordinator.activity.stream_count,
            "transcode_count": coordinator.activity.transcode_count,
            "direct_play_count": coordinator.activity.direct_play_count,
            "direct_stream_count": coordinator.activity.direct_stream_count,
            "total_bandwidth": coordinator.activity.total_bandwidth,
        }

    return {
        "entry": async_redact_data(entry.data, TO_REDACT),
        "tracearr": {
            "version": status.version,
            "healthy": status.healthy,
        },
        "servers": servers_data,
        "activity": activity_data,
        "users": {
            "total": len(coordinator.users) if coordinator.users else 0,
        },
    }
