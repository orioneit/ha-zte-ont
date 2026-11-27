"""Base entity for the ZTE ONT."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OntCoordinator


class OntEntity(CoordinatorEntity[OntCoordinator]):
    """Common device info."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OntCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        dev = coordinator.data.device
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="ZTE",
            model=dev.model or "F6005",
            hw_version=dev.hardware or None,
            sw_version=dev.software or None,
            serial_number=dev.serial or None,
        )
