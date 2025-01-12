"""Device representing a RAID, its drives, and all of its HA Entities."""

import asyncio

from dataclasses import dataclass, field
from enum import unique, StrEnum
from functools import cached_property

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers.entity import DeviceInfo

from ..const import DOMAIN
from ..devices.device import DeviceNotFoundError
from ..manufacturers import Manufacturer
from ..sources.source import get as get_source
from ..utils import async_cache

from .device import Device, DeviceSensor, StoreID
from .drive import Drive


@dataclass(frozen=True)
class RAIDID(StoreID):
  """Key used to uniquely identify RAIDs attached to a computer."""


@unique
class RAIDType(StrEnum):
  """State of a single drive within a RAID."""
  UNKNOWN = 'Unknown'  # Unrecognized/unsupported type.
  SPAN = 'Span'        # SPAN/BIG: Multiple drives concatenated into a larger one.  
  STRIPE = 'Stripe'    # RAID0: Data is striped across drives for performance.
  MIRROR = 'Mirror'    # RAID1: Data is mirrored across drives for redundancy.


@unique
class RAIDState(StrEnum):
  """State of either the overall RAID or a single drive within it."""
  UNKNOWN = 'Unknown'  # Unrecognized/unsupported state.
  ONLINE = 'Online'    # Online with no faults at the RAID level.
  OFFLINE = 'Offline'  # Offline or otherwise not working correctly.
  REBUILD = 'Rebuild'  # Online but rebuilding the mirror after a fault.


@dataclass
class RAIDDriveInfo:
  """Attributes and state for a single drive within a RAID."""
  id: str
  node: str
  state: RAIDState = RAIDState.UNKNOWN


@dataclass
class RAIDInfo:
  """RAID attributes and drive state."""
  name: str = 'Unknown'
  type: RAIDType = RAIDType.UNKNOWN
  state: RAIDState = RAIDState.UNKNOWN
  members: list[RAIDDriveInfo] = field(default_factory=list)
  capacity: int | None = None
  usage: int | None = None


class RAID(Device):
  """Device representing a RAID, its drives, and all of its HA Entities."""

  def __init__(self, store: RAIDID):
    super().__init__(store)

    self.drives: list[Drive] = []

    self.manufacturer: Manufacturer | None = None
    self.model: str | None = None

    self.state = DeviceSensor(
        self, 'State', icon='mdi:harddisk', value=RAIDState.UNKNOWN, values=RAIDState)
    self.capacity = DeviceSensor(
        self, 'Capacity',
        device_class=SensorDeviceClass.DATA_SIZE,
        unit_of_measurement='B',
        suggested_unit_of_measurement='TB',
        suggested_display_precision=2)
    self.usage = DeviceSensor(
        self, 'Usage',
        device_class=SensorDeviceClass.DATA_SIZE,
        unit_of_measurement='B',
        suggested_unit_of_measurement='TB',
        suggested_display_precision=2)

  @property
  def device_info(self) -> DeviceInfo:
    """Unique identifier that HA uses to group Entities under this Device."""
    return DeviceInfo(
        identifiers={(DOMAIN, self.id)},
        name=self.name,
        manufacturer=self.manufacturer.value,
        model=self.model,
    )

  @async_cache(ttl=10)  # Allow child Entities to call this without re-executing
  async def update(self):
    """Initializes the device's attributes and entities."""
    source = await get_source()
    try:
      info = await source.get_raid_info(self.node)
    except DeviceNotFoundError:
      return

    self.name = info.name
    self.manufacturer = Manufacturer.APPLE
    self.model = str(info.type)

    self.state.value = info.state
    self.capacity.value = info.capacity
    self.usage.value = info.usage
