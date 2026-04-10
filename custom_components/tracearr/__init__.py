"""The Tracearr integration."""

from __future__ import annotations

from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TracearrClient
from .coordinator import TracearrConfigEntry, TracearrDataUpdateCoordinator

PLATFORMS = [Platform.EVENT, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: TracearrConfigEntry) -> bool:
    """Set up Tracearr from a config entry."""
    api_client = TracearrClient(
        host=entry.data[CONF_HOST],
        api_key=entry.data[CONF_API_KEY],
        session=async_get_clientsession(hass, entry.data.get(CONF_VERIFY_SSL, True)),
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, True),
    )
    entry.runtime_data = TracearrDataUpdateCoordinator(hass, entry, api_client)
    await entry.runtime_data.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TracearrConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
