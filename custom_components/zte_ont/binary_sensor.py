"""Binary sensors for the ZTE ONT."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import OpticalData
from .coordinator import OntConfigEntry
from .entity import OntEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class OntBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[OpticalData], bool]


BINARY_SENSORS: tuple[OntBinaryDescription, ...] = (
    OntBinaryDescription(
        key="gpon_link",
        translation_key="gpon_link",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: d.state == 5,
    ),
    OntBinaryDescription(
        key="los",
        translation_key="los",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.los,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OntConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(OntBinarySensor(coordinator, d) for d in BINARY_SENSORS)


class OntBinarySensor(OntEntity, BinarySensorEntity):
    entity_description: OntBinaryDescription

    def __init__(self, coordinator, description: OntBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.data.optical)
