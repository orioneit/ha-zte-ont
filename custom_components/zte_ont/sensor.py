"""Sensors for the ZTE ONT."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import GPON_STATES, OpticalData
from .coordinator import OntConfigEntry
from .entity import OntEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class OntSensorDescription(SensorEntityDescription):
    value_fn: Callable[[OpticalData], float | str | None]


SENSORS: tuple[OntSensorDescription, ...] = (
    OntSensorDescription(
        key="gpon_state",
        translation_key="gpon_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(GPON_STATES.values()),
        value_fn=lambda d: d.state_name,
    ),
    OntSensorDescription(
        key="rx_power",
        translation_key="rx_power",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.rx_power,
    ),
    OntSensorDescription(
        key="tx_power",
        translation_key="tx_power",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.tx_power,
    ),
    OntSensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.temperature,
    ),
    OntSensorDescription(
        key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.voltage,
    ),
    OntSensorDescription(
        key="bias_current",
        translation_key="bias_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.bias_current,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OntConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(OntSensor(coordinator, d) for d in SENSORS)


class OntSensor(OntEntity, SensorEntity):
    entity_description: OntSensorDescription

    def __init__(self, coordinator, description: OntSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | str | None:
        return self.entity_description.value_fn(self.coordinator.data.optical)
