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
    TracearrLibrary,
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
        self.library: TracearrLibrary | None = None

    async def _async_update_data(self) -> None:
        """Get the latest data from Tracearr."""
        try:
            results = await asyncio.gather(
                self.api_client.async_get_sessions(),
                self.api_client.async_get_users(),
                self.api_client.async_get_servers(),
                self.api_client.async_get_library(),
            )
            self.activity = results[0]
            self.users = results[1]
            self.servers = results[2]
            self.library = results[3]
        except TracearrConnectionError as ex:
            raise UpdateFailed(ex) from ex
        except TracearrAuthenticationError as ex:
            raise ConfigEntryAuthFailed(ex) from ex
