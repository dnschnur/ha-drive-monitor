"""Monitors storage devices attached to the Home Assistant host machine."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, MANAGER_DATA_KEY, PLATFORMS
from .manager import DeviceManager


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
  """Creates a DeviceManager to discover devices and poll their attributes."""
  manager = DeviceManager(hass)

  # Make the DeviceManager available to async_setup_entry for each domain
  hass.data.setdefault(DOMAIN, {})[MANAGER_DATA_KEY] = manager

  # Discover attached devices and create Devices and HA Entities for them
  await manager.initialize()

  # Register the HA Entities for all of the managed devices
  await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

  return True  # Initialization successful


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
  """Removes all monitored devices from HA and unloads the integration."""
  if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
    hass.data[DOMAIN].pop(MANAGER_DATA_KEY)

  return unload_ok
