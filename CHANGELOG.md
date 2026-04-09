# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-09

### Added

- CI workflow with Ruff lint/format checks and pytest with coverage
- Pre-commit hooks for automated code quality (trailing-whitespace, YAML/JSON/TOML validation, Ruff)
- Dependabot configuration for automated pip and GitHub Actions dependency updates
- Full `pyproject.toml` project configuration (Ruff, pytest, coverage settings)
- `Final` type annotations in constants module
- `tests/conftest.py` with path setup for custom_components

### Changed

- Validate workflow now includes scheduled daily runs and manual dispatch triggers
- Expanded `.gitignore` with mypy, ruff, coverage, and pre-commit cache entries

### Removed

- Unused `aiohttp` import in config_flow and `Any` import in coordinator
- `aiohttp>=3.8.0` from manifest.json requirements (already bundled with Home Assistant)

## [0.0.1] - 2024-01-01

### Added

- Initial release
- Active streams sensor with per-session detail attributes
- Transcode, direct play, and direct stream count sensors
- Total, LAN, and WAN bandwidth sensors
- Total users and active violations sensors
- Connected servers sensor
- Total movies and total shows library sensors
- Config flow with host, API key, and SSL verification options
- Reauth support for expired or changed API keys
