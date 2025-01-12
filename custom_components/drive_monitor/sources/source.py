"""Abstract base class for classes that provide information about devices.

Different operating systems have different tools or libraries to query device
info. In some cases these overlap; e.g. on MacOS 'diskutil' is used to both
discover drives on the system and query RAID state.

Rather than having a single mega-class with confusing per-OS conditional logic,
the implementation is divided between Tools and Sources.

Tools, under the drive_monitor.tools package, wrap a single command-line tool
or library. If there is an existing library with a decent interface, it can
be added as a dependency and used directly; there's no need for a wrapper.

Sources, under the drive_monitor.sources package, exist for each supported OS,
and are named macos.py, linux.py, windows.py, etc. They use tools and libraries
to implement the Source interface.

The DeviceManager and Device classes use the Source.get() method to obtain the
Source implementation for the current OS, and use it to query devices.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import platform
import sys

from abc import abstractmethod, ABC
from functools import cache
from typing import TYPE_CHECKING

from ..utils import async_cache

if TYPE_CHECKING:
  from ..devices.drive import DriveID, DriveInfo
  from ..devices.raid import RAIDID, RAIDInfo


class Error(Exception):
  """Base class for exceptions raised by this package."""


class SourceNotFoundError(Error):
  """There is no Source implementation for the current platform."""


class Source(ABC):
  """Abstract base class for classes that provide information about devices."""

  @abstractmethod
  async def get_drives(self) -> list[DriveID]:
    """Returns keys for all physical drives present on the system.

    This includes drives that are grouped together into RAIDs.
    """

  @abstractmethod
  async def get_raids(self) -> list[RAIDID]:
    """Returns keys for all RAIDs present on the system."""

  @abstractmethod
  async def get_drive_info(self, node: str) -> DriveInfo:
    """Returns details and S.M.A.R.T. attributes for the given drive.

    Args:
      node: The drive's Device Node, e.g. 'disk3'.
    """

  @abstractmethod
  async def get_raid_info(self, node: str) -> RAIDInfo:
    """Returns details and state for the given RAID.

    Args:
      node: The RAID's Device Node, e.g. 'disk3'.
    """


@async_cache()
async def get() -> Source:
  """Returns the Source for the platform on which this program is running."""
  name = platform.system()
  if name == 'Darwin':
    name = 'MacOS'

  loop = asyncio.get_running_loop()
  module = await loop.run_in_executor(
      None, importlib.import_module, f'.{name.lower()}', __package__)
  for _, value in inspect.getmembers(module):
    if inspect.isclass(value) and issubclass(value, Source):
      return value()

  raise SourceNotFoundError(f'No Source defined for {name}')
