"""Abstract base class for monitored devices."""

from abc import abstractmethod, ABC
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Iterable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, Entity

SensorValue = str | int | float | date | datetime | Enum


class Error(Exception):
  """Base class for exceptions raised by this package."""


class DeviceNotFoundError(Error):
  """When querying a specific device, it could not be found."""


@dataclass(frozen=True)
class StoreID:
  """Key used to uniquely identify datastores attached to a computer.

  Attrs:
    id: Unique ID of the datastore, persistent across system restarts.
    node: Base of a datastore node, with any suffixes stripped; e.g. 'disk1'.
  """
  id: str
  node: str


class Device(ABC):
  """Abstract base class for monitored devices.

  Attrs:
    id: Unique ID of the device, persistent across system restarts.
    node: Base of a device node, with any suffixes stripped; e.g. 'disk1'.
    name: Human-readable name of the device, e.g. 'Macintosh HD'.
    entities: HA entities exposed by this device.
  """

  def __init__(self, store: StoreID):
    self.id: str = store.id
    self.node: str = store.node
    self.name: str | None = None

    # List of entities belonging to this devices. Entities automatically add
    # themselves to this list as they are created.
    self.entities: list[Entity] = []

  @property
  @abstractmethod
  def device_info(self) -> DeviceInfo:
    """Unique identifier that HA uses to group Entities under this Device."""

  @abstractmethod
  async def update(self):
    """Polls the state of the device's entities, and updates their values.

    This method should be annotated with @async_cache with a TTL. That's because
    Entities are normally all polled together, and this method will therefore be
    called many times. Even if the underlying data is cached, it's still better
    not to repeat setting all the attributes and sensor values unnecessarily.
    """


def entity_id(device_id: str, entity_name: str) -> str:
  """Returns an entity's ID, guaranteed to be unique within its domain."""
  return f'{device_id}_{entity_name}'


class DeviceEntity(Entity):
  """Base class for monitored device Entities."""

  _attr_has_entity_name = True
  _attr_should_poll = True

  def __init__(self, device: Device, name: str | None = None):
    """
    Args:
      device: Device that this entity is a part of.
      name: Human-readable name of the entity.
    """
    self.device = device

    self._attr_unique_id = entity_id(device.id, name) if name else device.id
    self._attr_name = name

    device.entities.append(self)

  @property
  def _attr_device_info(self):
    """Unique identifier that HA uses to group Entities under this Device.

    This is a property, rather than an attribute, because it must be computed
    lazily. Fields such as the device name aren't set yet when the Entity is
    created; they are populated later, by 'update'.
    """
    return self.device.device_info

  async def async_update(self):
    """Callback fired when HA polls the entity's current value or state."""
    await self.device.update()  # Cached w/ TTL, so fine for each entity to call


class DeviceSensor(SensorEntity, DeviceEntity):
  """Sensor entity for one of the device's attributes."""

  def __init__(self,
               device: Device,
               name: str | None = None,
               icon: str | None = None,
               device_class: SensorDeviceClass | None = None,
               unit_of_measurement: str | None = None,
               values: Iterable[SensorValue] | None = None,
               value: SensorValue | None = None):
    """
    Initializes a new sensor entity and attaches it to its device.

    Only the device is required; all other args are optional. Depending on the
    sensor, certain args may not make sense. E.g. a sensor with continuous
    measurements (e.g. temperature) wouldn't have a fixed 'values' list.

    Args:
      device: Device that this sensor is a part of.
      name: Human-readable name of the sensor.
      icon: Sensor's HA UI icon, e.g. 'mdi:thermometer'.
      device_class: Sensor's HA device class, e.g. 'voltage'.
      unit_of_measurement: Sensor's unit of measurement, e.g. 'kW'
      values: Sensor's set of possible values, e.g. ['open', 'closed'].
      value: Sensor's initial value.
    """
    super().__init__(device, name)

    if values and not device_class:
      device_class = SensorDeviceClass.ENUM

    self._attr_icon = icon
    self._attr_device_class = device_class
    self._attr_native_unit_of_measurement = unit_of_measurement

    if values:
      self._attr_options = [value.value if isinstance(value, Enum) else value for value in values]

    self.value = value

  @property
  def native_value(self) -> SensorValue | None:
    """The current sensor measurement in its native units."""
    if isinstance(self.value, Enum):
      return self.value.value
    return self.value
