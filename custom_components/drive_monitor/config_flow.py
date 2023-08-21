"""Configuration flow for the Drive Monitor integration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, INTEGRATION_NAME
from .types import YAML


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
  """Configuration flow for the Drive Monitor integration."""

  VERSION = 1

  async def async_step_user(self, user_input: YAML | None = None) -> FlowResult:
    """Entry point when the integration is added from the UI."""
    if self._async_current_entries():
      return self.async_abort(reason="single_instance_allowed")

    # Since devices are auto-discovered, we don't need any user configuration.
    # So rather than showing any form we'll just return an empty entry.
    return self.async_create_entry(title=INTEGRATION_NAME, data={})

  async def async_step_import(self, user_input: YAML) -> FlowResult:
    """Entry point when the integration is added from configuration.yaml."""
    return await self.async_step_user(user_input)
