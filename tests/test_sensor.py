"""Tests for the Tracearr sensor platform."""

import pytest

from custom_components.tracearr.api import (
    TracearrActivity,
    TracearrLibrary,
    TracearrServer,
    TracearrSessionData,
    TracearrUser,
)
from custom_components.tracearr.sensor import SENSOR_TYPES


class FakeCoordinator:
    """Fake coordinator for testing sensor value_fn callbacks."""

    def __init__(self, activity=None, users=None, servers=None, library=None):
        """Initialize with optional data."""
        self.activity = activity
        self.users = users
        self.servers = servers
        self.library = library


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
            lan_bandwidth=6000,
            wan_bandwidth=4000,
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
                    ip_address="192.168.1.10",
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
                    ip_address="192.168.1.11",
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

    @pytest.fixture
    def sample_library(self):
        """Return sample library data."""
        return TracearrLibrary(
            total_movies=500,
            total_shows=100,
            total_episodes=5000,
            total_music=200,
            total_storage=2048.5,
        )

    def _get_sensor(self, key):
        """Get a sensor description by key."""
        for sensor in SENSOR_TYPES:
            if sensor.key == key:
                return sensor
        raise ValueError(f"Sensor with key '{key}' not found")

    def test_active_streams(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test active_streams sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("active_streams")
        assert sensor.value_fn(coord) == 5

    def test_transcode_count(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test transcode_count sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("transcode_count")
        assert sensor.value_fn(coord) == 2

    def test_direct_play_count(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test direct_play_count sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("direct_play_count")
        assert sensor.value_fn(coord) == 2

    def test_direct_stream_count(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test direct_stream_count sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("direct_stream_count")
        assert sensor.value_fn(coord) == 1

    def test_total_bandwidth(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test total_bandwidth sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("total_bandwidth")
        assert sensor.value_fn(coord) == 10000

    def test_lan_bandwidth(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test lan_bandwidth sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("lan_bandwidth")
        assert sensor.value_fn(coord) == 6000

    def test_wan_bandwidth(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test wan_bandwidth sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("wan_bandwidth")
        assert sensor.value_fn(coord) == 4000

    def test_total_users(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test total_users sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("total_users")
        assert sensor.value_fn(coord) == 3

    def test_active_violations(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test active_violations sensor value (sum of all user violations)."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("active_violations")
        assert sensor.value_fn(coord) == 4  # 0 + 3 + 1

    def test_connected_servers(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test connected_servers sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("connected_servers")
        assert sensor.value_fn(coord) == 2

    def test_total_movies(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test total_movies sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("total_movies")
        assert sensor.value_fn(coord) == 500

    def test_total_shows(self, sample_activity, sample_users, sample_servers, sample_library):
        """Test total_shows sensor value."""
        coord = FakeCoordinator(
            activity=sample_activity,
            users=sample_users,
            servers=sample_servers,
            library=sample_library,
        )
        sensor = self._get_sensor("total_shows")
        assert sensor.value_fn(coord) == 100

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

    def test_expected_sensor_count(self):
        """Test that we have the expected number of sensors."""
        assert len(SENSOR_TYPES) == 12
