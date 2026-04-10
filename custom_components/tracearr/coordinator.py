"""Data update coordinator for the Tracearr integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    TracearrActivity,
    TracearrAuthenticationError,
    TracearrClient,
    TracearrConnectionError,
    TracearrServer,
    TracearrUser,
)
from .const import DOMAIN, LOGGER

type TracearrConfigEntry = ConfigEntry[TracearrDataUpdateCoordinator]


class TracearrDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """Data update coordinator for the Tracearr integration."""

    config_entry: TracearrConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: TracearrConfigEntry,
        api_client: TracearrClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.api_client = api_client
        self.activity: TracearrActivity | None = None
        self.users: list[TracearrUser] | None = None
        self.servers: list[TracearrServer] | None = None

        # Change-detection state for event entities.
        self._previous_session_ids: set[str] | None = None
        self._previous_violations: dict[str, int] | None = None
        self.pending_events: list[tuple[str, dict[str, Any]]] = []

    async def _async_update_data(self) -> None:
        """Get the latest data from Tracearr."""
        try:
            results = await asyncio.gather(
                self.api_client.async_get_sessions(),
                self.api_client.async_get_users(),
                self.api_client.async_get_servers(),
            )
            self.activity = results[0]
            self.users = results[1]
            self.servers = results[2]
        except TracearrConnectionError as ex:
            raise UpdateFailed(ex) from ex
        except TracearrAuthenticationError as ex:
            raise ConfigEntryAuthFailed(ex) from ex

        self._detect_events()

    def _detect_events(self) -> None:
        """Compare current data with previous state and queue events."""
        events: list[tuple[str, dict[str, Any]]] = []

        # --- Session change detection ---
        current_sessions = {
            s.session_id: s
            for s in (self.activity.sessions if self.activity else [])
            if s.session_id
        }
        current_ids = set(current_sessions)

        if self._previous_session_ids is not None:
            for sid in current_ids - self._previous_session_ids:
                session = current_sessions[sid]
                events.append(
                    (
                        "stream_started",
                        {
                            "user": session.user,
                            "title": session.title,
                            "media_type": session.media_type,
                            "device": session.device,
                            "quality": session.quality,
                        },
                    )
                )
            for sid in self._previous_session_ids - current_ids:
                events.append(
                    (
                        "stream_ended",
                        {"session_id": sid},
                    )
                )

        self._previous_session_ids = current_ids

        # --- Violation change detection ---
        current_violations = {u.user_id: u for u in (self.users or []) if u.user_id}

        if self._previous_violations is not None:
            for uid, user in current_violations.items():
                prev_count = self._previous_violations.get(uid, 0)
                if user.violations > prev_count:
                    events.append(
                        (
                            "violation_received",
                            {
                                "user": user.username,
                                "violations": user.violations,
                                "new_violations": user.violations - prev_count,
                            },
                        )
                    )

        self._previous_violations = {
            uid: u.violations for uid, u in current_violations.items()
        }

        self.pending_events = events
