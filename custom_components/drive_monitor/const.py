"""Constants shared across the integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

# Official HASS identifier for this integration.
DOMAIN: Final = "drive_monitor"

# User-friendly name of this integration
INTEGRATION_NAME: Final = "Drive Monitor"

# Key in the HA data object for the global DeviceManager instance.
MANAGER_DATA_KEY: Final = 'manager'

# List of HA platforms that monitored devices can create entities for.
PLATFORMS: Final[list[Platform]] = [Platform.SENSOR]

# How often to poll for device updates.
SCAN_INTERVAL = timedelta(seconds=20)
