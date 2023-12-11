"""Device representing a physical drive and all of its HA Entities."""

import asyncio
import logging
import typing

from dataclasses import dataclass
from enum import unique, StrEnum

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers.entity import DeviceInfo

from ..const import DOMAIN
from ..devices.device import DeviceNotFoundError
from ..manufacturers import Manufacturer
from ..sources.source import Source
from ..utils import async_cache

from .device import Device, DeviceSensor, StoreID

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DriveID(StoreID):
  """Key used to uniquely identify drives attached to a computer.

  Attrs:
    raid: Unique ID of the RAID to which this drive belongs, if any.
  """
  raid: str | None = None


@unique
class DriveState(StrEnum):
  """Physical drive type/interface."""
  UNKNOWN = 'Unknown'  # Unknown/unrecognized state.
  HEALTHY = 'Healthy'  # Drive is passing S.M.A.R.T. checks.
  UNHEALTHY = 'Unhealthy'  # Drive is failing S.M.A.R.T. checks.


@unique
class DriveType(StrEnum):
  """Physical drive type/interface."""
  UNKNOWN = 'Unknown'  # Unrecognized/unsupported type.
  HDD = 'HDD'  # Spinning magnetic disk
  NVME = 'NVMe'  # NVMe SSD


@dataclass
class SSDInfo:
  """Additional attributes specific to solid-state disks."""
  bytes_read: int | None = None
  bytes_written: int | None = None
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
  """Device representing a physical drive and all of its HA Entities.

  Attributes:
    raid: ID of the RAID that this drive belongs to, if any.
  """

  def __init__(self, store: DriveID):
    super().__init__(store)

    self.raid: str | None = store.raid

    self.manufacturer: Manufacturer | None = None
    self.model: str | None = None
    self.firmware_version: str | None = None

    self.state = DeviceSensor(
        self, 'State', icon='mdi:harddisk', value=DriveState.UNKNOWN, values=DriveState)

    # RAID member drives don't have their own capacity and usage.
    if not self.raid:
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
    except DeviceNotFoundError:  # Most likely a removable drive
      LOGGER.info('Drive %s could no longer be found; it may have been removed.', self.name)
      return

    self.name = info.name
    self.manufacturer = info.manufacturer
    self.model = info.model
    self.firmware_version = info.firmware_version

    self.state.value = DriveState.HEALTHY if info.smart_passed else DriveState.UNHEALTHY
    if not self.raid:
      self.capacity.value = info.capacity
      self.usage.value = info.usage
    self.temperature.value = info.temperature
