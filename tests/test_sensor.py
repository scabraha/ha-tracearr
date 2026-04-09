"""Tests for the Tracearr sensor platform."""

import pytest

from custom_components.tracearr.api import (
    TracearrActivity,
    TracearrServer,
    TracearrSessionData,
    TracearrUser,
)
from custom_components.tracearr.sensor import SENSOR_TYPES


class FakeCoordinator:
    """Fake coordinator for testing sensor value_fn callbacks."""

    def __init__(self, activity=None, users=None, servers=None):
        """Initialize with optional data."""
        self.activity = activity
        self.users = users
        self.servers = servers


class TestSensorValueFunctions:
    """Test all sensor value_fn callbacks."""

    @pytest.fixture
    def sample_activity(self):
        """Return sample activity data."""
        return TracearrActivity(
            stream_count=5,
            transcode_count=2,
            direct_play_count=2,
            direct_stream_count=1,
            total_bandwidth=10000,
            sessions=[
                TracearrSessionData(
                    session_id="1",
                    user="alice",
                    title="Movie A",
                    media_type="movie",
                    state="playing",
                    progress=30,
                    quality="1080p",
                    device="Chromecast",
                ),
                TracearrSessionData(
                    session_id="2",
                    user="bob",
                    title="Show B",
                    media_type="episode",
                    state="paused",
                    progress=60,
                    quality="4K",
                    device="AppleTV",
                ),
            ],
        )

    @pytest.fixture
    def sample_users(self):
        """Return sample user data."""
        return [
            TracearrUser(user_id="1", username="alice", trust_score=90.0, violations=0),
            TracearrUser(user_id="2", username="bob", trust_score=70.0, violations=3),
            TracearrUser(user_id="3", username="carol", trust_score=80.0, violations=1),
        ]

    @pytest.fixture
    def sample_servers(self):
        """Return sample server data."""
        return [
            TracearrServer(
                server_id="s1", name="Plex", server_type="plex", status="connected"
            ),
            TracearrServer(
                server_id="s2", name="Jellyfin", server_type="jellyfin", status="connected"
            ),
        ]

    def _get_sensor(self, key):
        """Get a sensor description by key."""
        for sensor in SENSOR_TYPES:
            if sensor.key == key:
                return sensor
        raise ValueError(f"Sensor with key '{key}' not found")

    def test_active_streams(self, sample_activity, sample_users, sample_servers):
        """Test active_streams sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
        )
        sensor = self._get_sensor("active_streams")
        assert sensor.value_fn(coord) == 5

    def test_transcode_count(self, sample_activity, sample_users, sample_servers):
        """Test transcode_count sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
        )
        sensor = self._get_sensor("transcode_count")
        assert sensor.value_fn(coord) == 2

    def test_direct_play_count(self, sample_activity, sample_users, sample_servers):
        """Test direct_play_count sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
        )
        sensor = self._get_sensor("direct_play_count")
        assert sensor.value_fn(coord) == 2

    def test_direct_stream_count(self, sample_activity, sample_users, sample_servers):
        """Test direct_stream_count sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
        )
        sensor = self._get_sensor("direct_stream_count")
        assert sensor.value_fn(coord) == 1

    def test_total_bandwidth(self, sample_activity, sample_users, sample_servers):
        """Test total_bandwidth sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
        )
        sensor = self._get_sensor("total_bandwidth")
        assert sensor.value_fn(coord) == 10000

    def test_total_users(self, sample_activity, sample_users, sample_servers):
        """Test total_users sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
        )
        sensor = self._get_sensor("total_users")
        assert sensor.value_fn(coord) == 3

    def test_active_violations(self, sample_activity, sample_users, sample_servers):
        """Test active_violations sensor value (sum of all user violations)."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
        )
        sensor = self._get_sensor("active_violations")
        assert sensor.value_fn(coord) == 4  # 0 + 3 + 1

    def test_connected_servers(self, sample_activity, sample_users, sample_servers):
        """Test connected_servers sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
        )
        sensor = self._get_sensor("connected_servers")
        assert sensor.value_fn(coord) == 2

    def test_sensors_return_none_when_no_data(self):
        """Test all sensors return None when coordinator has no data."""
        coord = FakeCoordinator()
        for sensor in SENSOR_TYPES:
            assert sensor.value_fn(coord) is None, f"{sensor.key} should return None"

    def test_all_sensor_keys_unique(self):
        """Test that all sensor keys are unique."""
        keys = [s.key for s in SENSOR_TYPES]
        assert len(keys) == len(set(keys)), "Sensor keys must be unique"

    def test_all_sensor_translation_keys_unique(self):
        """Test that all sensor translation keys are unique."""
        t_keys = [s.translation_key for s in SENSOR_TYPES]
        assert len(t_keys) == len(set(t_keys)), "Translation keys must be unique"

    def test_all_sensors_have_explicit_name(self):
        """Test that all sensors have an explicit name set for reliable display."""
        for sensor in SENSOR_TYPES:
            assert sensor.name is not None, (
                f"Sensor '{sensor.key}' must have an explicit name"
            )
            assert isinstance(sensor.name, str), (
                f"Sensor '{sensor.key}' name must be a string"
            )

    def test_expected_sensor_count(self):
        """Test that we have the expected number of sensors."""
        assert len(SENSOR_TYPES) == 8

    def test_all_sensors_have_icons(self):
        """Test that all sensors have an explicit icon set."""
        expected_icons = {
            "active_streams": "mdi:play-network",
            "transcode_count": "mdi:sync",
            "direct_play_count": "mdi:play-circle",
            "direct_stream_count": "mdi:cast-connected",
            "total_bandwidth": "mdi:speedometer",
            "total_users": "mdi:account-group",
            "active_violations": "mdi:shield-alert",
            "connected_servers": "mdi:server-network",
        }
        for sensor in SENSOR_TYPES:
            assert sensor.icon is not None, (
                f"Sensor '{sensor.key}' must have an icon"
            )
            assert sensor.icon == expected_icons[sensor.key], (
                f"Sensor '{sensor.key}' has unexpected icon '{sensor.icon}'"
            )

    def test_optional_sensors_disabled_by_default(self):
        """Test that optional sensors are disabled by default."""
        disabled_keys = {"transcode_count", "direct_play_count", "direct_stream_count"}
        for sensor in SENSOR_TYPES:
            if sensor.key in disabled_keys:
                assert sensor.entity_registry_enabled_default is False, (
                    f"Sensor '{sensor.key}' should be disabled by default"
                )
            else:
                assert sensor.entity_registry_enabled_default is True, (
                    f"Sensor '{sensor.key}' should be enabled by default"
                )

    def test_diagnostic_sensors_have_entity_category(self):
        """Test that diagnostic sensors have the correct entity category."""
        from homeassistant.const import EntityCategory

        diagnostic_keys = {"total_users", "connected_servers"}
        for sensor in SENSOR_TYPES:
            if sensor.key in diagnostic_keys:
                assert sensor.entity_category == EntityCategory.DIAGNOSTIC, (
                    f"Sensor '{sensor.key}' should have DIAGNOSTIC entity category"
                )
            else:
                assert sensor.entity_category is None, (
                    f"Sensor '{sensor.key}' should not have an entity category"
                )
