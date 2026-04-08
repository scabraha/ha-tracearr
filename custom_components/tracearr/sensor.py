"""Sensor platform for the Tracearr integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import TracearrConfigEntry, TracearrDataUpdateCoordinator
from .entity import TracearrEntity


@dataclass(frozen=True, kw_only=True)
class TracearrSensorEntityDescription(SensorEntityDescription):
    """Describe a Tracearr sensor."""

    value_fn: Callable[[TracearrDataUpdateCoordinator], StateType]


SENSOR_TYPES: tuple[TracearrSensorEntityDescription, ...] = (
    TracearrSensorEntityDescription(
        key="active_streams",
        translation_key="active_streams",
        native_unit_of_measurement="Streams",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coord: coord.activity.stream_count
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="transcode_count",
        translation_key="transcode_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="Streams",
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.activity.transcode_count
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="direct_play_count",
        translation_key="direct_play_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="Streams",
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.activity.direct_play_count
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="direct_stream_count",
        translation_key="direct_stream_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="Streams",
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.activity.direct_stream_count
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="total_bandwidth",
        translation_key="total_bandwidth",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfInformation.KILOBITS,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coord: coord.activity.total_bandwidth
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="lan_bandwidth",
        translation_key="lan_bandwidth",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfInformation.KILOBITS,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.activity.lan_bandwidth
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="wan_bandwidth",
        translation_key="wan_bandwidth",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfInformation.KILOBITS,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.activity.wan_bandwidth
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="total_users",
        translation_key="total_users",
        native_unit_of_measurement="Users",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coord: len(coord.users) if coord.users is not None else None,
    ),
    TracearrSensorEntityDescription(
        key="active_violations",
        translation_key="active_violations",
        native_unit_of_measurement="Violations",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coord: sum(u.violations for u in coord.users)
        if coord.users
        else None,
    ),
    TracearrSensorEntityDescription(
        key="connected_servers",
        translation_key="connected_servers",
        native_unit_of_measurement="Servers",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coord: len(coord.servers)
        if coord.servers is not None
        else None,
    ),
    TracearrSensorEntityDescription(
        key="total_movies",
        translation_key="total_movies",
        native_unit_of_measurement="Movies",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.library.total_movies
        if coord.library
        else None,
    ),
    TracearrSensorEntityDescription(
        key="total_shows",
        translation_key="total_shows",
        native_unit_of_measurement="Shows",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.library.total_shows
        if coord.library
        else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TracearrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Tracearr sensors based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        TracearrSensor(coordinator, description) for description in SENSOR_TYPES
    )


class TracearrSensor(TracearrEntity, SensorEntity):
    """Define a Tracearr sensor."""

    entity_description: TracearrSensorEntityDescription

    def __init__(
        self,
        coordinator: TracearrDataUpdateCoordinator,
        description: TracearrSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, str | list] | None:
        """Return extra state attributes for the active_streams sensor."""
        if self.entity_description.key != "active_streams":
            return None
        if not self.coordinator.activity or not self.coordinator.activity.sessions:
            return None
        return {
            "sessions": [
                {
                    "user": session.user,
                    "title": session.title,
                    "media_type": session.media_type,
                    "state": session.state,
                    "progress": session.progress,
                    "quality": session.quality,
                    "device": session.device,
                }
                for session in self.coordinator.activity.sessions
            ]
        }
