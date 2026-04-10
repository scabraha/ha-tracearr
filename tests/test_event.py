"""Tests for the Tracearr event platform and coordinator event detection."""

from custom_components.tracearr.api import (
    TracearrActivity,
    TracearrSessionData,
    TracearrUser,
)
from custom_components.tracearr.event import EVENT_TYPES


class FakeCoordinator:
    """Minimal fake coordinator for testing detect_events logic."""

    def __init__(self, activity=None, users=None):
        """Initialize with optional data."""
        self.activity = activity
        self.users = users
        self._previous_sessions = None
        self._previous_violations = None
        self.pending_events = []
        self.activity_log = []

    def detect_events(self):
        """Run the change-detection logic (copied from the real coordinator)."""
        from custom_components.tracearr.coordinator import (
            TracearrDataUpdateCoordinator,
        )

        TracearrDataUpdateCoordinator.detect_events(self)


class TestEventDetection:
    """Tests for the coordinator event detection logic."""

    def test_first_update_no_events(self):
        """First update should seed state and produce no events."""
        coord = FakeCoordinator(
            activity=TracearrActivity(
                stream_count=1,
                sessions=[
                    TracearrSessionData(
                        session_id="s1",
                        user="alice",
                        title="Movie",
                        media_type="movie",
                    ),
                ],
            ),
            users=[
                TracearrUser(user_id="u1", username="alice", violations=2),
            ],
        )
        coord.detect_events()

        assert coord.pending_events == []
        assert set(coord._previous_sessions) == {"s1"}
        assert coord._previous_violations == {"u1": 2}

    def test_new_session_fires_stream_started(self):
        """New sessions should generate stream_started events."""
        coord = FakeCoordinator(
            activity=TracearrActivity(sessions=[]),
            users=[],
        )
        # Seed initial state.
        coord.detect_events()
        assert coord.pending_events == []

        # Add a new session.
        coord.activity = TracearrActivity(
            stream_count=1,
            sessions=[
                TracearrSessionData(
                    session_id="s1",
                    user="alice",
                    title="Inception",
                    media_type="movie",
                    state="playing",
                    device="Chromecast",
                    quality="1080p",
                ),
            ],
        )
        coord.detect_events()

        assert len(coord.pending_events) == 1
        event_type, attrs = coord.pending_events[0]
        assert event_type == "stream_started"
        assert attrs["user"] == "alice"
        assert attrs["title"] == "Inception"
        assert attrs["media_type"] == "movie"
        assert attrs["state"] == "playing"
        assert attrs["device"] == "Chromecast"
        assert attrs["quality"] == "1080p"

    def test_removed_session_fires_stream_ended(self):
        """Removed sessions should generate stream_ended events with details."""
        coord = FakeCoordinator(
            activity=TracearrActivity(
                sessions=[
                    TracearrSessionData(
                        session_id="s1",
                        user="alice",
                        title="Movie",
                        media_type="movie",
                        device="Roku",
                        quality="4K",
                    ),
                ],
            ),
            users=[],
        )
        coord.detect_events()

        # Remove the session.
        coord.activity = TracearrActivity(sessions=[])
        coord.detect_events()

        assert len(coord.pending_events) == 1
        event_type, attrs = coord.pending_events[0]
        assert event_type == "stream_ended"
        assert attrs["session_id"] == "s1"
        assert attrs["user"] == "alice"
        assert attrs["title"] == "Movie"
        assert attrs["media_type"] == "movie"
        assert attrs["device"] == "Roku"
        assert attrs["quality"] == "4K"

    def test_violation_increase_fires_violation_received(self):
        """Increased violation count should generate violation_received event."""
        coord = FakeCoordinator(
            activity=TracearrActivity(sessions=[]),
            users=[
                TracearrUser(
                    user_id="u1",
                    username="bob",
                    violations=1,
                    trust_score=90.0,
                ),
            ],
        )
        coord.detect_events()
        assert coord.pending_events == []

        # Increase violation count.
        coord.users = [
            TracearrUser(
                user_id="u1",
                username="bob",
                violations=3,
                trust_score=80.0,
            ),
        ]
        coord.detect_events()

        assert len(coord.pending_events) == 1
        event_type, attrs = coord.pending_events[0]
        assert event_type == "violation_received"
        assert attrs["user"] == "bob"
        assert attrs["violations"] == 3
        assert attrs["new_violations"] == 2
        assert attrs["trust_score"] == 80.0

    def test_violation_same_count_no_event(self):
        """Same violation count should not generate events."""
        coord = FakeCoordinator(
            activity=TracearrActivity(sessions=[]),
            users=[
                TracearrUser(user_id="u1", username="bob", violations=3),
            ],
        )
        coord.detect_events()
        coord.detect_events()

        assert coord.pending_events == []

    def test_violation_decrease_no_event(self):
        """Decreased violation count should not generate events."""
        coord = FakeCoordinator(
            activity=TracearrActivity(sessions=[]),
            users=[
                TracearrUser(user_id="u1", username="bob", violations=5),
            ],
        )
        coord.detect_events()

        coord.users = [
            TracearrUser(user_id="u1", username="bob", violations=3),
        ]
        coord.detect_events()

        assert coord.pending_events == []

    def test_new_user_with_violations_fires_event(self):
        """A newly appeared user with violations should fire an event."""
        coord = FakeCoordinator(
            activity=TracearrActivity(sessions=[]),
            users=[],
        )
        coord.detect_events()

        coord.users = [
            TracearrUser(
                user_id="u1",
                username="carol",
                violations=2,
                trust_score=75.0,
            ),
        ]
        coord.detect_events()

        assert len(coord.pending_events) == 1
        event_type, attrs = coord.pending_events[0]
        assert event_type == "violation_received"
        assert attrs["user"] == "carol"
        assert attrs["new_violations"] == 2
        assert attrs["trust_score"] == 75.0

    def test_multiple_events_in_single_update(self):
        """Multiple changes in one update should produce multiple events."""
        coord = FakeCoordinator(
            activity=TracearrActivity(
                sessions=[
                    TracearrSessionData(session_id="s1", user="alice"),
                ],
            ),
            users=[
                TracearrUser(user_id="u1", username="bob", violations=0),
            ],
        )
        coord.detect_events()

        # s1 ends, s2 starts, bob gets a violation.
        coord.activity = TracearrActivity(
            sessions=[
                TracearrSessionData(
                    session_id="s2",
                    user="carol",
                    title="Show",
                    media_type="episode",
                ),
            ],
        )
        coord.users = [
            TracearrUser(user_id="u1", username="bob", violations=1),
        ]
        coord.detect_events()

        event_types = [e[0] for e in coord.pending_events]
        assert "stream_started" in event_types
        assert "stream_ended" in event_types
        assert "violation_received" in event_types
        assert len(coord.pending_events) == 3

    def test_no_activity_data(self):
        """None activity should not crash."""
        coord = FakeCoordinator(activity=None, users=None)
        coord.detect_events()
        assert coord.pending_events == []

        coord.detect_events()
        assert coord.pending_events == []

    def test_empty_session_id_ignored(self):
        """Sessions with empty session_id should be excluded from tracking."""
        coord = FakeCoordinator(
            activity=TracearrActivity(
                sessions=[
                    TracearrSessionData(session_id="", user="alice"),
                ],
            ),
            users=[],
        )
        coord.detect_events()
        assert set(coord._previous_sessions) == set()

    def test_activity_log_populated(self):
        """Activity log should accumulate entries from detected events."""
        coord = FakeCoordinator(
            activity=TracearrActivity(sessions=[]),
            users=[],
        )
        coord.detect_events()
        assert coord.activity_log == []

        coord.activity = TracearrActivity(
            stream_count=1,
            sessions=[
                TracearrSessionData(
                    session_id="s1",
                    user="alice",
                    title="Movie",
                    media_type="movie",
                ),
            ],
        )
        coord.detect_events()

        assert len(coord.activity_log) == 1
        entry = coord.activity_log[0]
        assert entry["event_type"] == "stream_started"
        assert entry["user"] == "alice"
        assert entry["title"] == "Movie"
        assert "timestamp" in entry

    def test_activity_log_capped(self):
        """Activity log should not exceed MAX_ACTIVITY_LOG_ENTRIES."""
        from custom_components.tracearr.coordinator import MAX_ACTIVITY_LOG_ENTRIES

        coord = FakeCoordinator(
            activity=TracearrActivity(sessions=[]),
            users=[],
        )
        coord.detect_events()

        # Generate more than MAX entries by repeatedly adding/removing sessions.
        for i in range(MAX_ACTIVITY_LOG_ENTRIES + 10):
            coord.activity = TracearrActivity(
                sessions=[
                    TracearrSessionData(
                        session_id=f"s{i}",
                        user="alice",
                        title=f"Movie {i}",
                        media_type="movie",
                    ),
                ],
            )
            coord.detect_events()

        assert len(coord.activity_log) <= MAX_ACTIVITY_LOG_ENTRIES


class TestEventEntityDefinition:
    """Tests for the event entity definitions."""

    def test_event_types_defined(self):
        """Test that event types are defined."""
        assert "stream_started" in EVENT_TYPES
        assert "stream_ended" in EVENT_TYPES
        assert "violation_received" in EVENT_TYPES

    def test_event_types_count(self):
        """Test the number of event types."""
        assert len(EVENT_TYPES) == 3
