"""Device representing a physical drive and all of its HA Entities."""

import asyncio
import typing

from dataclasses import dataclass
from enum import unique, Enum

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers.entity import DeviceInfo

from ..const import DOMAIN
from ..devices.device import NodeNotFoundError
from ..manufacturers import Manufacturer
from ..sources.source import Source
from ..utils import async_cache

from .device import Device, DeviceSensor, StoreID


@unique
class DriveState(Enum):
  """Physical drive type/interface."""
  UNKNOWN = 'Unknown'  # Unknown/unrecognized state.
  HEALTHY = 'Healthy'  # Drive is passing S.M.A.R.T. checks.
  UNHEALTHY = 'Unhealthy'  # Drive is failing S.M.A.R.T. checks.


@unique
class DriveType(Enum):
  """Physical drive type/interface."""
  UNKNOWN = 'Unknown'  # Unrecognized/unsupported type.
  HDD = 'HDD'  # Spinning magnetic disk
  NVME = 'NVMe'  # NVMe SSD


@dataclass
class SSDInfo:
  """Additional attributes specific to solid-state disks."""
  available_spare: int | None = None
  available_spare_threshold: int | None = None
  unsafe_shutdowns: int | None = None


@dataclass
class DriveInfo:
  """Physical drive info and S.M.A.R.T attributes."""
  name: str = 'Unknown'
  type: DriveType = DriveType.UNKNOWN
  manufacturer: Manufacturer = Manufacturer.UNKNOWN
  model: str = 'Unknown'
  serial_number: str = 'Unknown'
  firmware_version: str = 'Unknown'
  smart_passed: bool | None = None
  capacity: int | None = None
  usage: int | None = None
  temperature: int | None = None
  ssd_info: SSDInfo | None = None


class Drive(Device):
  """Device representing a physical drive and all of its HA Entities."""

  def __init__(self, store: StoreID):
    super().__init__(store)

    self.manufacturer: Manufacturer | None = None
    self.model: str | None = None
    self.firmware_version: str | None = None

    self.state = DeviceSensor(
        self, 'State', icon='mdi:harddisk', value=DriveState.UNKNOWN, values=DriveState)
    self.capacity = DeviceSensor(
        self, 'Capacity',
        device_class=SensorDeviceClass.DATA_SIZE,
        unit_of_measurement='B')
    self.usage = DeviceSensor(
        self, 'Usage',
        device_class=SensorDeviceClass.DATA_SIZE,
        unit_of_measurement='B')
    self.temperature = DeviceSensor(
        self, 'Temperature',
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement='°C')

  @property
  def device_info(self) -> DeviceInfo:
    """Unique identifier that HA uses to group Entities under this Device."""
    return DeviceInfo(
        identifiers={(DOMAIN, self.id)},
        name=self.name,
        manufacturer=self.manufacturer,
        model=self.model,
        sw_version=self.firmware_version,
    )

  @async_cache(ttl=10)  # Allow child Entities to call this without re-executing
  async def update(self):
    """Updates all of the device's attributes and entities."""
    try:
      info = await Source.get().get_drive_info(self.node)
    except NodeNotFoundError:  # Most likely a removable drive
      return

    self.name = info.name
    self.manufacturer = info.manufacturer
    self.model = info.model
    self.firmware_version = info.firmware_version

    self.state.value = DriveState.HEALTHY if info.smart_passed else DriveState.UNHEALTHY
    self.capacity.value = info.capacity
    self.usage.value = info.usage
    self.temperature.value = info.temperature
