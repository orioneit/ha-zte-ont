"""Config flow for the ZTE ONT."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.core import callback

from . import build_client
from .api import DEFAULT_HOST_HEADER, OntAuthError, OntBusyError, OntData, OntError
from .const import (
    CONF_HOST_HEADER,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PORT_SCHEMA = vol.All(vol.Coerce(int), vol.Range(min=1, max=65535))


class OntConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def _try(self, data: dict[str, Any]) -> tuple[OntData | None, str | None]:
        try:
            return await build_client(self.hass, data).fetch(), None
        except OntAuthError as err:
            _LOGGER.warning("ONT login failed: %s", err)
            return None, "invalid_auth"
        except OntBusyError as err:
            _LOGGER.warning("ONT busy: %s", err)
            return None, "busy"
        except OntError as err:
            _LOGGER.warning("Cannot reach the ONT: %s", err)
            return None, "cannot_connect"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error")
            return None, "unknown"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_HOST: user_input[CONF_HOST].strip(),
                CONF_PORT: user_input[CONF_PORT],
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_HOST_HEADER: user_input.get(CONF_HOST_HEADER, "").strip() or DEFAULT_HOST_HEADER,
            }
            ont, error = await self._try(data)
            if ont is not None:
                await self.async_set_unique_id(ont.device.serial or f"{data[CONF_HOST]}:{data[CONF_PORT]}")
                self._abort_if_unique_id_configured(updates=data)
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or f"ONT {ont.device.model}", data=data
                )
            errors["base"] = error
        defaults = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME, "ONT")): str,
                    vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, DEFAULT_HOST_HEADER)): str,
                    vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): PORT_SCHEMA,
                    vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, DEFAULT_USERNAME)): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_HOST_HEADER, default=defaults.get(CONF_HOST_HEADER, DEFAULT_HOST_HEADER)
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {**entry.data, **user_input}
            ont, error = await self._try(data)
            if ont is not None:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=entry.data[CONF_USERNAME]): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return OntOptionsFlow()


class OntOptionsFlow(OptionsFlow):
    """Options: polling interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=86400)),
                }
            ),
        )
