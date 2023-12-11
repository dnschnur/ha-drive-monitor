"""Adds sensors for all monitored devices to HA."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANAGER_DATA_KEY, SCAN_INTERVAL


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices: AddEntitiesCallback):
  """Adds sensors for all monitored devices to HA."""
  manager = hass.data[DOMAIN][MANAGER_DATA_KEY]
  await manager.add_entities(async_add_devices, SensorEntity)
