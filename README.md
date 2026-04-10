# Tracearr Integration for Home Assistant

![Tracearr](https://cdn.jsdelivr.net/gh/selfhst/icons@main/png/tracearr.png)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A custom [Home Assistant](https://www.home-assistant.io/) integration for [Tracearr](https://docs.tracearr.com/) — a real-time monitoring, analytics, and account-sharing detection platform for Plex, Jellyfin, and Emby media servers.

This integration exposes sensors similar to the [Tautulli integration](https://www.home-assistant.io/integrations/tautulli/), providing real-time insight into your media server activity directly in Home Assistant.

## Features

- **Active Streams** — Number of currently active streams across all connected media servers, with per-session detail attributes (user, title, media type, state, progress, quality, device).
- **Transcode / Direct Play / Direct Stream Counts** — Breakdown of current stream types.
- **Bandwidth Monitoring** — Total, LAN, and WAN bandwidth usage.
- **User Monitoring** — Total number of tracked users and aggregated violation counts.
- **Server Status** — Number of connected media servers (Plex, Jellyfin, Emby).
- **Library Statistics** — Total movies and TV shows in your media libraries.

## Prerequisites

- A running [Tracearr](https://docs.tracearr.com/) instance accessible over HTTP or HTTPS.
- A Tracearr API key (found under **Settings → API** in the Tracearr web UI).
- [HACS](https://hacs.xyz/) installed in your Home Assistant instance.

## Installation

### HACS (Recommended)

1. Open Home Assistant and navigate to **HACS → Integrations**.
2. Click the **three dots** menu in the top right corner and select **Custom repositories**.
3. Add this repository URL:
   ```
   https://github.com/scabraha/ha-tracearr
   ```
   and select **Integration** as the category.
4. Click **Add**, then find **Tracearr** in the HACS integration list.
5. Click **Download** and restart Home Assistant.

### Manual Installation

1. Download or clone this repository.
2. Copy the `custom_components/tracearr` folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

## Configuration

1. In Home Assistant, go to **Settings → Devices & Services → Add Integration**.
2. Search for **Tracearr** and select it.
3. Enter the following:
   - **Host** — The full URL of your Tracearr instance (e.g., `http://192.168.1.100:8080` or `https://tracearr.example.com`).
   - **API Key** — Your Tracearr API key.
   - **Verify SSL** — Whether to verify SSL certificates (default: enabled).
4. Click **Submit**. The integration will validate the connection and create sensors.

## Sensors

| Sensor | Icon | Description | Unit | Category | Default Enabled |
|---|---|---|---|---|---|
| **Active streams** | `mdi:play-network` | Number of currently active streams | Streams | — | ✅ |
| **Transcodes** | `mdi:sync` | Number of streams being transcoded | Streams | — | ❌ |
| **Direct plays** | `mdi:play-circle` | Number of direct play streams | Streams | — | ❌ |
| **Direct streams** | `mdi:cast-connected` | Number of direct streams | Streams | — | ❌ |
| **Total bandwidth** | `mdi:speedometer` | Total bandwidth usage | kbit/s | — | ✅ |
| **Active violations** | `mdi:shield-alert` | Sum of all user violations | Violations | — | ✅ |
| **Total users** | `mdi:account-group` | Number of tracked users | Users | Diagnostic | ✅ |
| **Connected servers** | `mdi:server-network` | Number of connected media servers | Servers | Diagnostic | ✅ |
| **Recent activity** | `mdi:history` | Number of recent activity events (streams started/ended, violations) | Events | — | ✅ |

### Enabling Optional Sensors

Some sensors are **disabled by default** to keep the dashboard clean (marked ❌ above). To enable them:

1. Go to **Settings → Devices & Services → Tracearr**.
2. Click on the **Tracearr** device.
3. Under **Sensors**, click on **N entities not shown** to reveal hidden entities.
4. Click on the disabled sensor you want to enable (e.g., **Transcodes**).
5. Toggle the **Enabled** switch to **on**.
6. Click **Update** — the sensor will start collecting data on the next polling cycle.

### Diagnostic Sensors

Sensors with the **Diagnostic** category (Total users, Connected servers) provide supplementary information about the Tracearr system. These appear under the **Diagnostic** section on the device page rather than the main controls.

### Active Streams Attributes

The **Active streams** sensor includes extra state attributes with per-session details:

```yaml
sessions:
  - user: "alice"
    title: "Inception"
    media_type: "movie"
    state: "playing"
    progress: 45
    quality: "1080p"
    device: "Chromecast"
  - user: "bob"
    title: "Breaking Bad S01E01"
    media_type: "episode"
    state: "paused"
    progress: 20
    quality: "4K"
    device: "Apple TV"
```

### Recent Activity Attributes

The **Recent activity** sensor maintains a rolling log (up to 25 entries) of detected activity events. The state value is the count of logged entries, and the `entries` attribute contains the full list (newest first):

```yaml
entries:
  - event_type: "stream_started"
    timestamp: "2025-01-15T20:30:00+00:00"
    user: "alice"
    title: "Inception"
    media_type: "movie"
    state: "playing"
    device: "Chromecast"
    quality: "1080p"
  - event_type: "stream_ended"
    timestamp: "2025-01-15T20:15:00+00:00"
    session_id: "abc123"
    user: "bob"
    title: "Breaking Bad S01E01"
    media_type: "episode"
    device: "Apple TV"
    quality: "4K"
  - event_type: "violation_received"
    timestamp: "2025-01-15T20:00:00+00:00"
    user: "carol"
    violations: 3
    new_violations: 1
    trust_score: 75.0
```

### Events

The integration fires Home Assistant events through an **Activity** event entity for real-time automation triggers. Each event includes detailed context:

| Event Type | Description | Attributes |
|---|---|---|
| `stream_started` | A new stream has begun | `user`, `title`, `media_type`, `state`, `device`, `quality` |
| `stream_ended` | A stream has stopped | `session_id`, `user`, `title`, `media_type`, `device`, `quality` |
| `violation_received` | A user received new violation(s) | `user`, `violations`, `new_violations`, `trust_score` |

## Example Automations

### Notify when streams exceed a threshold

```yaml
automation:
  - alias: "High stream count alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.tracearr_active_streams
        above: 5
    action:
      - service: notify.mobile_app
        data:
          title: "Tracearr Alert"
          message: "There are {{ states('sensor.tracearr_active_streams') }} active streams!"
```

### Alert on new violations

```yaml
automation:
  - alias: "Violation alert"
    trigger:
      - platform: state
        entity_id: sensor.tracearr_active_violations
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state | int > trigger.from_state.state | int }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Tracearr Violation"
          message: "New account sharing violation detected! Total: {{ states('sensor.tracearr_active_violations') }}"
```

## Development

### Running Tests

```bash
pip install pytest pytest-asyncio aiohttp aioresponses homeassistant
python -m pytest tests/ -v
```

### Project Structure

```
ha-tracearr/
├── custom_components/
│   └── tracearr/
│       ├── __init__.py          # Integration setup and teardown
│       ├── api.py               # Async API client for Tracearr REST API
│       ├── config_flow.py       # UI-based configuration flow
│       ├── const.py             # Constants (domain, logger, etc.)
│       ├── coordinator.py       # DataUpdateCoordinator for polling
│       ├── entity.py            # Base entity class
│       ├── manifest.json        # Integration metadata for HA and HACS
│       ├── sensor.py            # Sensor entity definitions
│       └── strings.json         # UI strings and translations
├── tests/
│   ├── test_api.py              # API client and data model tests
│   └── test_sensor.py           # Sensor value function tests
├── hacs.json                    # HACS metadata
├── pyproject.toml               # Python project config
└── README.md
```

## Tracearr API Reference

This integration uses the following Tracearr REST API endpoints:

| Endpoint | Description |
|---|---|
| `GET /api/status` | System health and version info |
| `GET /api/sessions` | Current active streams/sessions |
| `GET /api/users` | User list with trust scores and violations |
| `GET /api/servers` | Connected media server status |
| `GET /api/library` | Library content statistics |

All requests use Bearer token authentication via the API key. Full API documentation is available at your Tracearr instance's `/api-docs` endpoint.

## License

This project is provided as-is under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

