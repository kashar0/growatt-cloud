"""Sensor platform for Growatt Cloud integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


@dataclass(frozen=True)
class GrowattSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with Growatt-specific fields."""
    # List of possible API field names (first found is used)
    api_keys: tuple[str, ...] = ()
    # Optional divisor (some fields are returned x10 by some API versions)
    scale: float = 1.0


SENSORS: tuple[GrowattSensorDescription, ...] = (
    # ── Power ──────────────────────────────────────────────────────────────────
    GrowattSensorDescription(
        key="pvpowerin",
        name="PV Input Power",
        api_keys=("ppv", "pvPower", "inputPower"),
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvpowerout",
        name="AC Output Power",
        api_keys=("pac", "outPutPower", "acPower", "power"),
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pv1watt",
        name="PV String 1 Power",
        api_keys=("ppv1", "pPv1"),
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pv2watt",
        name="PV String 2 Power",
        api_keys=("ppv2", "pPv2"),
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvgridpower",
        name="Grid Power Phase R",
        api_keys=("pacr", "rPac"),
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvgridpower2",
        name="Grid Power Phase S",
        api_keys=("pacs", "sPac"),
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvgridpower3",
        name="Grid Power Phase T",
        api_keys=("pact", "tPac"),
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── Voltage ────────────────────────────────────────────────────────────────
    GrowattSensorDescription(
        key="pv1voltage",
        name="PV String 1 Voltage",
        api_keys=("vpv1", "vPv1"),
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pv2voltage",
        name="PV String 2 Voltage",
        api_keys=("vpv2", "vPv2"),
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvgridvoltage",
        name="Grid Voltage Phase R",
        api_keys=("vacr", "rVac", "vac1"),
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvgridvoltage2",
        name="Grid Voltage Phase S",
        api_keys=("vacs", "sVac", "vac2"),
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvgridvoltage3",
        name="Grid Voltage Phase T",
        api_keys=("vact", "tVac", "vac3"),
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="Vac_RS",
        name="Grid Voltage L1-L2",
        api_keys=("vacRs", "vacrs"),
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="Vac_ST",
        name="Grid Voltage L2-L3",
        api_keys=("vacSt", "vacst"),
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="Vac_TR",
        name="Grid Voltage L3-L1",
        api_keys=("vacTr", "vactr"),
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pbusvolt",
        name="DC Bus Voltage+",
        api_keys=("pBusVoltage", "busvolt"),
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="nbusvolt",
        name="DC Bus Voltage-",
        api_keys=("nBusVoltage",),
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── Current ────────────────────────────────────────────────────────────────
    GrowattSensorDescription(
        key="pv1current",
        name="PV String 1 Current",
        api_keys=("ipv1", "iPv1"),
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pv2current",
        name="PV String 2 Current",
        api_keys=("ipv2", "iPv2"),
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvgridcurrent",
        name="Grid Current Phase R",
        api_keys=("iacr", "rIac", "iac1"),
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvgridcurrent2",
        name="Grid Current Phase S",
        api_keys=("iacs", "sIac", "iac2"),
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvgridcurrent3",
        name="Grid Current Phase T",
        api_keys=("iact", "tIac", "iac3"),
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── Energy ─────────────────────────────────────────────────────────────────
    GrowattSensorDescription(
        key="pvenergytoday",
        name="Energy Today",
        api_keys=("eacToday", "eAcToday", "todayEnergy", "eToday"),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GrowattSensorDescription(
        key="pvenergytotal",
        name="Energy Total",
        api_keys=("eacTotal", "eAcTotal", "totalEnergy", "energy"),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GrowattSensorDescription(
        key="epv1today",
        name="PV String 1 Energy Today",
        api_keys=("epv1Today", "ePv1Today"),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GrowattSensorDescription(
        key="epv1total",
        name="PV String 1 Energy Total",
        api_keys=("epv1Total", "ePv1Total"),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GrowattSensorDescription(
        key="epv2today",
        name="PV String 2 Energy Today",
        api_keys=("epv2Today", "ePv2Today"),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GrowattSensorDescription(
        key="epv2total",
        name="PV String 2 Energy Total",
        api_keys=("epv2Total", "ePv2Total"),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GrowattSensorDescription(
        key="epvtotal",
        name="PV Total Energy",
        api_keys=("epvTotal", "ePvTotal"),
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # ── Temperature ────────────────────────────────────────────────────────────
    GrowattSensorDescription(
        key="pvtemperature",
        name="Inverter Temperature",
        api_keys=("temperature", "inverterTemp"),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvipmtemperature",
        name="IPM Temperature",
        api_keys=("temperature2", "ipmTemp"),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvboottemperature",
        name="Boost Temperature",
        api_keys=("temperature3", "boostTemp"),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── Misc ───────────────────────────────────────────────────────────────────
    GrowattSensorDescription(
        key="pvfrequentie",
        name="Grid Frequency",
        api_keys=("fac", "gridFreq", "frequency"),
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="pvstatus",
        name="Inverter Status",
        api_keys=("status", "inverterStatus"),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GrowattSensorDescription(
        key="totworktime",
        name="Total Work Time",
        api_keys=("timeTotal", "workTimeTotal"),
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GrowattSensor(coordinator, description)
        for description in SENSORS
    )


class GrowattSensor(CoordinatorEntity, SensorEntity):
    """A single Growatt sensor entity."""

    entity_description: GrowattSensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, description: GrowattSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        device_sn = coordinator.entry.data["device_sn"]
        self._attr_unique_id = f"{device_sn}_{description.key}"

    @property
    def device_info(self) -> dict[str, Any]:
        return self.coordinator.device_info

    @property
    def native_value(self) -> float | int | str | None:
        data = self.coordinator.data
        if not data:
            return None
        for key in self.entity_description.api_keys:
            val = data.get(key)
            if val is not None:
                try:
                    f = float(val)
                    scale = self.entity_description.scale
                    return round(f / scale, 2) if scale != 1.0 else (int(f) if f == int(f) else round(f, 2))
                except (TypeError, ValueError):
                    return str(val)
        return None

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None
