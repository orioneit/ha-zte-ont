"""Data update coordinator for the ZTE ONT."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OntAuthError, OntBusyError, OntData, OntError, ZteOnt
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type OntConfigEntry = ConfigEntry[OntCoordinator]

# A login can fail for transient reasons (e.g. the web UI is in use),
# so ask for new credentials only after several rejections in a row.
AUTH_FAILURES_BEFORE_REAUTH = 3


class OntCoordinator(DataUpdateCoordinator[OntData]):
    """Polls the ONT web UI."""

    config_entry: OntConfigEntry

    def __init__(self, hass: HomeAssistant, entry: OntConfigEntry, client: ZteOnt) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        self._auth_failures = 0

    async def _async_update_data(self) -> OntData:
        try:
            data = await self.client.fetch()
        except OntAuthError as err:
            self._auth_failures += 1
            if self._auth_failures >= AUTH_FAILURES_BEFORE_REAUTH:
                raise ConfigEntryAuthFailed(str(err)) from err
            raise UpdateFailed(str(err)) from err
        except OntBusyError as err:
            raise UpdateFailed(str(err)) from err
        except OntError as err:
            raise UpdateFailed(str(err)) from err
        self._auth_failures = 0
        return data
