"""Manages the set of devices (drives, RAIDs) being monitored."""

from __future__ import annotations

import asyncio
import itertools
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .devices.device import Device
from .devices.drive import Drive
from .devices.raid import RAID
from .sources.source import Source

LOGGER = logging.getLogger(__name__)


class DeviceManager:
  """Manages the set of devices (drives, RAIDs) being monitored.

  When initialized, DeviceManager discovers all of the devices present in the
  system, and creates Device wrapper objects to represent them. These wrappers
  hold a list of Entities for each device, which are added to Home Assistant by
  their corresponding entity platform module.

  Attributes:
    drives: List of physical drives being managed.
        Includes drives that are members of a RAID.
    raids: List of RAIDs being managed.
  """

  def __init__(self, hass: HomeAssistant):
    self.drives: dict[str, Drive] = {}
    self.raids: dict[str, RAID] = {}

    self._hass: HomeAssistant = hass

  async def add_entities(self, async_add_devices: AddEntitiesCallback, entity_class: type[Entity]):
    """Adds all entities of the given type, from all monitored devices, to HA.

    Args:
      async_add_devices: HA add entity callback passed from async_setup_entry.
      entity_class: Entity subclass to filter on.
    """
    entities = []
    for device in itertools.chain(self.drives.values(), self.raids.values()):
      entities.extend(entity for entity in device.entities if isinstance(entity, entity_class))
    async_add_devices(entities, update_before_add=True)

  async def initialize(self):
    """Initializes the set of drives and RAIDs being managed.

    Prior to calling this method, the 'drives' and 'raids' attributes are empty
    dicts. After this method returns, they are populated with Drives and RAIDs.
    """
    source = Source.get()
    drives, raids = await asyncio.gather(source.get_drives(), source.get_raids())

    for info in drives:
      self.drives[info.node] = Drive(info)

    for info in raids:
      self.raids[info.node] = RAID(info)

    LOGGER.info(f'Discovered {len(drives)} drives and {len(raids)} RAIDs.')