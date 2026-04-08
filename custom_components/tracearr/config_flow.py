"""Config flow for the Tracearr integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_VERIFY_SSL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    TracearrAuthenticationError,
    TracearrClient,
    TracearrConnectionError,
    TracearrError,
)
from .const import DEFAULT_NAME, DOMAIN


class TracearrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tracearr."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            error = await self._validate_input(user_input)
            if error is None:
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data=user_input,
                )
            errors["base"] = error

        user_input = user_input or {}
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=user_input.get(CONF_HOST, "")
                ): str,
                vol.Required(
                    CONF_API_KEY, default=user_input.get(CONF_API_KEY, "")
                ): str,
                vol.Optional(
                    CONF_VERIFY_SSL,
                    default=user_input.get(CONF_VERIFY_SSL, True),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a reauthorization flow request."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth dialog."""
        errors: dict[str, str] = {}
        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            updated = {**reauth_entry.data, CONF_API_KEY: user_input[CONF_API_KEY]}
            error = await self._validate_input(updated)
            if error is None:
                return self.async_update_reload_and_abort(reauth_entry, data=updated)
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def _validate_input(self, user_input: dict[str, Any]) -> str | None:
        """Validate the user input by connecting to Tracearr."""
        verify_ssl = user_input.get(CONF_VERIFY_SSL, True)
        try:
            client = TracearrClient(
                host=user_input[CONF_HOST],
                api_key=user_input[CONF_API_KEY],
                session=async_get_clientsession(self.hass, verify_ssl),
                verify_ssl=verify_ssl,
            )
            await client.async_get_status()
        except TracearrConnectionError:
            return "cannot_connect"
        except TracearrAuthenticationError:
            return "invalid_auth"
        except TracearrError:
            return "unknown"
        return None
