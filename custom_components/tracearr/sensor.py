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
from homeassistant.const import EntityCategory, UnitOfDataRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api import TracearrServer
from .coordinator import TracearrConfigEntry, TracearrDataUpdateCoordinator
from .entity import TracearrEntity


@dataclass(frozen=True, kw_only=True)
class TracearrSensorEntityDescription(SensorEntityDescription):
    """Describe a Tracearr sensor."""

    value_fn: Callable[[TracearrDataUpdateCoordinator], StateType]


@dataclass(frozen=True, kw_only=True)
class TracearrServerSensorEntityDescription(SensorEntityDescription):
    """Describe a per-server Tracearr sensor."""

    server_value_fn: Callable[[TracearrServer], StateType]


SENSOR_TYPES: tuple[TracearrSensorEntityDescription, ...] = (
    TracearrSensorEntityDescription(
        key="active_streams",
        translation_key="active_streams",
        name="Active streams",
        icon="mdi:play-network",
        native_unit_of_measurement="Streams",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coord: coord.activity.stream_count
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="transcode_count",
        translation_key="transcode_count",
        name="Transcodes",
        icon="mdi:sync",
        native_unit_of_measurement="Streams",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.activity.transcode_count
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="direct_play_count",
        translation_key="direct_play_count",
        name="Direct plays",
        icon="mdi:play-circle",
        native_unit_of_measurement="Streams",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.activity.direct_play_count
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="direct_stream_count",
        translation_key="direct_stream_count",
        name="Direct streams",
        icon="mdi:cast-connected",
        native_unit_of_measurement="Streams",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.activity.direct_stream_count
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="total_bandwidth",
        translation_key="total_bandwidth",
        name="Total bandwidth",
        icon="mdi:speedometer",
        native_unit_of_measurement=UnitOfDataRate.KILOBITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coord: coord.activity.total_bandwidth
        if coord.activity
        else None,
    ),
    TracearrSensorEntityDescription(
        key="total_users",
        translation_key="total_users",
        name="Total users",
        icon="mdi:account-group",
        native_unit_of_measurement="Users",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coord: len(coord.users) if coord.users is not None else None,
    ),
    TracearrSensorEntityDescription(
        key="active_violations",
        translation_key="active_violations",
        name="Active violations",
        icon="mdi:shield-alert",
        native_unit_of_measurement="Violations",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coord: sum(u.violations for u in coord.users)
        if coord.users
        else None,
    ),
    TracearrSensorEntityDescription(
        key="connected_servers",
        translation_key="connected_servers",
        name="Connected servers",
        icon="mdi:server-network",
        native_unit_of_measurement="Servers",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coord: len(coord.servers)
        if coord.servers is not None
        else None,
    ),
)

SERVER_SENSOR_TYPES: tuple[TracearrServerSensorEntityDescription, ...] = (
    TracearrServerSensorEntityDescription(
        key="server_status",
        translation_key="server_status",
        name="Status",
        icon="mdi:server",
        server_value_fn=lambda server: server.status,
    ),
    TracearrServerSensorEntityDescription(
        key="server_active_streams",
        translation_key="server_active_streams",
        name="Active streams",
        icon="mdi:play-network",
        native_unit_of_measurement="Streams",
        state_class=SensorStateClass.MEASUREMENT,
        server_value_fn=lambda server: server.active_streams,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TracearrConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tracearr sensors based on a config entry."""
    coordinator = entry.runtime_data

    entities: list[TracearrSensor | TracearrServerSensor] = [
        TracearrSensor(coordinator, description) for description in SENSOR_TYPES
    ]

    if coordinator.servers:
        for server in coordinator.servers:
            for description in SERVER_SENSOR_TYPES:
                entities.append(
                    TracearrServerSensor(
                        coordinator, description, server.server_id, server.name
                    )
                )

    async_add_entities(entities)


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


class TracearrServerSensor(TracearrEntity, SensorEntity):
    """Define a per-server Tracearr sensor."""

    entity_description: TracearrServerSensorEntityDescription

    def __init__(
        self,
        coordinator: TracearrDataUpdateCoordinator,
        description: TracearrServerSensorEntityDescription,
        server_id: str,
        server_name: str,
    ) -> None:
        """Initialize the per-server sensor."""
        super().__init__(coordinator, description)
        self._server_id = server_id
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{server_id}_{description.key}"
        self._attr_name = f"{server_name} {description.name}"

    def _get_server(self) -> TracearrServer | None:
        """Look up this sensor's server from the coordinator data."""
        if self.coordinator.servers is None:
            return None
        for server in self.coordinator.servers:
            if server.server_id == self._server_id:
                return server
        return None

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        server = self._get_server()
        if server is None:
            return None
        return self.entity_description.server_value_fn(server)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return extra state attributes including server type."""
        server = self._get_server()
        if server is None:
            return None
        return {
            "server_type": server.server_type,
        }
