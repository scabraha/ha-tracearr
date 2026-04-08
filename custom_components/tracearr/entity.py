"""Base entity for the Tracearr integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import TracearrDataUpdateCoordinator


class TracearrEntity(CoordinatorEntity[TracearrDataUpdateCoordinator]):
    """Define a base Tracearr entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TracearrDataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the Tracearr entity."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self.entity_description = description
        self._attr_device_info = DeviceInfo(
            configuration_url=coordinator.api_client.base_url,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry_id)},
            manufacturer=DEFAULT_NAME,
            name=DEFAULT_NAME,
        )
