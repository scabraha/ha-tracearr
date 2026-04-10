"""Data update coordinator for the Tracearr integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    TracearrActivity,
    TracearrAuthenticationError,
    TracearrClient,
    TracearrConnectionError,
    TracearrServer,
    TracearrSessionData,
    TracearrUser,
)
from .const import DOMAIN, LOGGER

type TracearrConfigEntry = ConfigEntry[TracearrDataUpdateCoordinator]

MAX_ACTIVITY_LOG_ENTRIES = 25


def _stream_message(verb: str, session: TracearrSessionData) -> str:
    """Build a human-readable message for a stream event."""
    parts = [session.user or "Unknown user", verb]
    if session.title:
        parts.append(session.title)
    if session.device:
        parts.append(f"on {session.device}")
    if session.quality:
        parts.append(f"({session.quality})")
    return " ".join(parts)


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
        self._previous_sessions: dict[str, TracearrSessionData] | None = None
        self._previous_violations: dict[str, int] | None = None
        self.pending_events: list[tuple[str, dict[str, Any]]] = []
        self.activity_log: list[dict[str, Any]] = []

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

        self.detect_events()

    def detect_events(self) -> None:
        """Compare current data with previous state and queue events."""
        events: list[tuple[str, dict[str, Any]]] = []
        now = dt_util.utcnow().isoformat()

        # --- Session change detection ---
        current_sessions = {
            s.session_id: s
            for s in (self.activity.sessions if self.activity else [])
            if s.session_id
        }
        current_ids = set(current_sessions)

        if self._previous_sessions is not None:
            previous_ids = set(self._previous_sessions)
            for sid in current_ids - previous_ids:
                session = current_sessions[sid]
                events.append(
                    (
                        "stream_started",
                        {
                            "user": session.user,
                            "title": session.title,
                            "media_type": session.media_type,
                            "state": session.state,
                            "device": session.device,
                            "quality": session.quality,
                            "message": _stream_message("started watching", session),
                        },
                    )
                )
            for sid in previous_ids - current_ids:
                prev_session = self._previous_sessions[sid]
                events.append(
                    (
                        "stream_ended",
                        {
                            "session_id": sid,
                            "user": prev_session.user,
                            "title": prev_session.title,
                            "media_type": prev_session.media_type,
                            "device": prev_session.device,
                            "quality": prev_session.quality,
                            "message": _stream_message(
                                "stopped watching", prev_session
                            ),
                        },
                    )
                )

        self._previous_sessions = dict(current_sessions)

        # --- Violation change detection ---
        current_violations = {u.user_id: u for u in (self.users or []) if u.user_id}

        if self._previous_violations is not None:
            for uid, user in current_violations.items():
                prev_count = self._previous_violations.get(uid, 0)
                if user.violations > prev_count:
                    new_count = user.violations - prev_count
                    events.append(
                        (
                            "violation_received",
                            {
                                "user": user.username,
                                "violations": user.violations,
                                "new_violations": new_count,
                                "trust_score": user.trust_score,
                                "message": (
                                    f"{user.username} received {new_count} new "
                                    f"violation{'s' if new_count != 1 else ''} "
                                    f"(total: {user.violations}, "
                                    f"trust score: {user.trust_score})"
                                ),
                            },
                        )
                    )

        self._previous_violations = {
            uid: u.violations for uid, u in current_violations.items()
        }

        self.pending_events = events

        # --- Append to rolling activity log (newest first) ---
        new_entries = [
            {"event_type": event_type, "timestamp": now, **attrs}
            for event_type, attrs in events
        ]
        self.activity_log = (list(reversed(new_entries)) + self.activity_log)[
            :MAX_ACTIVITY_LOG_ENTRIES
        ]
