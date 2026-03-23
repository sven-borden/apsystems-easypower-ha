"""AP Systems EasyPower sensors."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import APSystemsCoordinator


@dataclass(frozen=True)
class APSystemsSensorDescription(SensorEntityDescription):
    """Describes a sensor with a data source key and path."""
    # source: "realtime" or "statistic"
    source: str = "statistic"
    # path: key name in the source dict
    path: str = ""
    # optional factor
    factor: float = 1.0


SENSOR_DESCRIPTIONS: tuple[APSystemsSensorDescription, ...] = (
    APSystemsSensorDescription(
        key="power",
        name="Current Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        source="realtime",
        path="power",
    ),
    APSystemsSensorDescription(
        key="power_ch1",
        name="Power Channel 1",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        source="realtime",
        path="power1",
    ),
    APSystemsSensorDescription(
        key="power_ch2",
        name="Power Channel 2",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        source="realtime",
        path="power2",
    ),
    APSystemsSensorDescription(
        key="energy_today",
        name="Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        source="statistic",
        path="todayEnergy",
    ),
    APSystemsSensorDescription(
        key="energy_month",
        name="Energy This Month",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        source="statistic",
        path="monthEnergy",
    ),
    APSystemsSensorDescription(
        key="energy_lifetime",
        name="Energy Lifetime",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        source="statistic",
        path="lifetimeEnergy",
    ),
    APSystemsSensorDescription(
        key="last_power",
        name="Last Reported Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        source="statistic",
        path="lastPower",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AP Systems EasyPower sensors from config entry."""
    coordinator: APSystemsCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities = []
    for inv in coordinator.inverters:
        dev_id = inv["inverter_dev_id"]
        dev_name = inv.get("device_name") or dev_id
        model = inv.get("model", "EZ Inverter")

        for desc in SENSOR_DESCRIPTIONS:
            entities.append(APSystemsSensor(coordinator, desc, entry, dev_id, dev_name, model))

    async_add_entities(entities)


class APSystemsSensor(CoordinatorEntity[APSystemsCoordinator], SensorEntity):
    """Represents a single AP Systems EasyPower sensor."""

    entity_description: APSystemsSensorDescription

    def __init__(
        self,
        coordinator: APSystemsCoordinator,
        description: APSystemsSensorDescription,
        entry: ConfigEntry,
        dev_id: str,
        dev_name: str,
        model: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._dev_id = dev_id
        self._attr_unique_id = f"{entry.entry_id}_{dev_id}_{description.key}"
        # Use inverter alias + sensor name for friendly display
        self._attr_name = f"{dev_name} {description.name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, dev_id)},
            "name": dev_name,
            "manufacturer": "APsystems",
            "model": model,
            "via_device": (DOMAIN, entry.entry_id),
        }

    @property
    def _inv_data(self) -> dict:
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get(self._dev_id, {})

    @property
    def available(self) -> bool:
        """Power sensors are unavailable when inverter is offline; energy sensors stay available."""
        if not super().available:
            return False
        if not self._inv_data:
            return False
        # Realtime-based sensors (power) are unavailable when offline
        if self.entity_description.source == "realtime" and self._inv_data.get("offline", False):
            return False
        return True

    @property
    def native_value(self) -> float | None:
        """Return current sensor value from coordinator data."""
        source_data = self._inv_data.get(self.entity_description.source, {})
        raw = source_data.get(self.entity_description.path)
        if raw is None:
            return None
        try:
            return float(raw) * self.entity_description.factor
        except (TypeError, ValueError):
            return None
