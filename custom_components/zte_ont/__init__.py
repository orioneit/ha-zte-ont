"""The ZTE GPON ONT integration."""

from __future__ import annotations

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant

from .api import ZteOnt
from .const import CONF_HOST_HEADER
from .coordinator import OntConfigEntry, OntCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


def build_client(hass: HomeAssistant, data: dict) -> ZteOnt:
    return ZteOnt(
        data[CONF_HOST],
        data[CONF_PORT],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        data.get(CONF_HOST_HEADER, ""),
    )


async def async_setup_entry(hass: HomeAssistant, entry: OntConfigEntry) -> bool:
    """Set up the ONT from a config entry."""
    coordinator = OntCoordinator(hass, entry, build_client(hass, entry.data))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OntConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: OntConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
