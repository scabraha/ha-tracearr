"""Event platform for the Tracearr integration."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TracearrConfigEntry, TracearrDataUpdateCoordinator
from .entity import TracearrEntity

EVENT_TYPES: list[str] = [
    "stream_started",
    "stream_ended",
    "violation_received",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TracearrConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tracearr event entities based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([TracearrActivityEvent(coordinator)])


class TracearrActivityEvent(TracearrEntity, EventEntity):
    """Event entity that surfaces Tracearr activity in the HA activity pane."""

    _attr_translation_key = "activity"
    _attr_event_types = EVENT_TYPES
    _attr_icon = "mdi:history"
    _attr_name = "Activity"

    def __init__(self, coordinator: TracearrDataUpdateCoordinator) -> None:
        """Initialize the event entity."""
        super().__init__(
            coordinator,
            EntityDescription(key="activity"),
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator data updates and fire queued events."""
        for event_type, event_attributes in self.coordinator.pending_events:
            self._trigger_event(event_type, event_attributes)
        self.coordinator.pending_events = []
        self.async_write_ha_state()
